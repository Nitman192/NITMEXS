"""Repository for persistent proctor alert lifecycle tracking."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any, Protocol


class ProctorAlertRepository(Protocol):
    def upsert_open_alert(
        self,
        attempt_id: str,
        exam_id: str,
        student_id: str,
        indicator_code: str,
        indicator_payload: dict[str, Any] | None,
        detected_at: str,
    ) -> tuple[dict[str, Any], bool]: ...

    def get_alert(self, alert_id: str) -> dict[str, Any] | None: ...

    def list_alerts(
        self,
        exam_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]: ...

    def list_unresolved_alerts(
        self,
        exam_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]: ...

    def list_unresolved_alerts_for_sync(
        self,
        exam_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def get_alert_summary(self, exam_id: str | None = None) -> dict[str, Any]: ...

    def list_alerts_for_metrics(
        self,
        exam_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def acknowledge_alert(
        self,
        alert_id: str,
        actor_id: str,
        acknowledged_at: str,
    ) -> dict[str, Any] | None: ...

    def resolve_alert(
        self,
        alert_id: str,
        actor_id: str,
        resolved_at: str,
        resolution_note: str | None = None,
    ) -> dict[str, Any] | None: ...


class SQLiteProctorAlertRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def upsert_open_alert(
        self,
        attempt_id: str,
        exam_id: str,
        student_id: str,
        indicator_code: str,
        indicator_payload: dict[str, Any] | None,
        detected_at: str,
    ) -> tuple[dict[str, Any], bool]:
        row = self._conn.execute(
            """
            SELECT id
            FROM proctor_alerts
            WHERE attempt_id = ?
              AND indicator_code = ?
              AND status IN ('open', 'acknowledged')
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (attempt_id, indicator_code),
        ).fetchone()

        payload_json = json.dumps(indicator_payload or {}, separators=(",", ":"))
        if row is not None:
            alert_id = row["id"]
            self._conn.execute(
                """
                UPDATE proctor_alerts
                SET last_detected_at = ?,
                    detection_count = detection_count + 1,
                    indicator_payload_json = ?
                WHERE id = ?
                """,
                (detected_at, payload_json, alert_id),
            )
            updated = self.get_alert(alert_id)
            if updated is None:
                raise RuntimeError("Failed to fetch updated proctor alert")
            return updated, False

        alert_id = str(uuid.uuid4())
        try:
            self._conn.execute(
                """
                INSERT INTO proctor_alerts(
                    id, attempt_id, exam_id, student_id, indicator_code,
                    indicator_payload_json, status, detection_count,
                    first_detected_at, last_detected_at, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, 'open', 1, ?, ?, ?)
                """,
                (
                    alert_id,
                    attempt_id,
                    exam_id,
                    student_id,
                    indicator_code,
                    payload_json,
                    detected_at,
                    detected_at,
                    detected_at,
                ),
            )
        except sqlite3.IntegrityError:
            conflict = self._conn.execute(
                """
                SELECT id
                FROM proctor_alerts
                WHERE attempt_id = ?
                  AND indicator_code = ?
                  AND status IN ('open', 'acknowledged')
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (attempt_id, indicator_code),
            ).fetchone()
            if conflict is None:
                raise
            self._conn.execute(
                """
                UPDATE proctor_alerts
                SET last_detected_at = ?,
                    detection_count = detection_count + 1,
                    indicator_payload_json = ?
                WHERE id = ?
                """,
                (detected_at, payload_json, conflict["id"]),
            )
            updated = self.get_alert(conflict["id"])
            if updated is None:
                raise RuntimeError("Failed to fetch conflicted proctor alert")
            return updated, False
        created = self.get_alert(alert_id)
        if created is None:
            raise RuntimeError("Failed to fetch newly created proctor alert")
        return created, True

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT
                id, attempt_id, exam_id, student_id,
                indicator_code, indicator_payload_json,
                status, detection_count,
                first_detected_at, last_detected_at, created_at,
                acknowledged_at, acknowledged_by,
                resolved_at, resolved_by, resolution_note
            FROM proctor_alerts
            WHERE id = ?
            """,
            (alert_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def list_alerts(
        self,
        exam_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT
                id, attempt_id, exam_id, student_id,
                indicator_code, indicator_payload_json,
                status, detection_count,
                first_detected_at, last_detected_at, created_at,
                acknowledged_at, acknowledged_by,
                resolved_at, resolved_by, resolution_note
            FROM proctor_alerts
            WHERE (? IS NULL OR exam_id = ?)
              AND (? IS NULL OR status = ?)
            ORDER BY last_detected_at DESC, id DESC
            LIMIT ?
            """,
            (exam_id, exam_id, status, status, limit),
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_unresolved_alerts(
        self,
        exam_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT
                id, attempt_id, exam_id, student_id,
                indicator_code, indicator_payload_json,
                status, detection_count,
                first_detected_at, last_detected_at, created_at,
                acknowledged_at, acknowledged_by,
                resolved_at, resolved_by, resolution_note
            FROM proctor_alerts
            WHERE (? IS NULL OR exam_id = ?)
              AND status IN ('open', 'acknowledged')
            ORDER BY last_detected_at DESC, id DESC
            LIMIT ?
            """,
            (exam_id, exam_id, limit),
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def list_unresolved_alerts_for_sync(
        self,
        exam_id: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT
                id, attempt_id, exam_id, student_id,
                indicator_code, indicator_payload_json,
                status, detection_count,
                first_detected_at, last_detected_at, created_at,
                acknowledged_at, acknowledged_by,
                resolved_at, resolved_by, resolution_note
            FROM proctor_alerts
            WHERE (? IS NULL OR exam_id = ?)
              AND status IN ('open', 'acknowledged')
            ORDER BY last_detected_at DESC, id DESC
            """,
            (exam_id, exam_id),
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def get_alert_summary(self, exam_id: str | None = None) -> dict[str, Any]:
        status_rows = self._conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM proctor_alerts
            WHERE (? IS NULL OR exam_id = ?)
            GROUP BY status
            """,
            (exam_id, exam_id),
        ).fetchall()
        status_counts = {row["status"]: int(row["count"]) for row in status_rows}

        indicator_rows = self._conn.execute(
            """
            SELECT
                indicator_code,
                COUNT(*) AS total_count,
                SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_count,
                SUM(CASE WHEN status = 'acknowledged' THEN 1 ELSE 0 END) AS acknowledged_count,
                SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) AS resolved_count
            FROM proctor_alerts
            WHERE (? IS NULL OR exam_id = ?)
            GROUP BY indicator_code
            ORDER BY total_count DESC, indicator_code ASC
            """,
            (exam_id, exam_id),
        ).fetchall()

        exam_rows = self._conn.execute(
            """
            SELECT
                exam_id,
                COUNT(*) AS total_count,
                SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_count,
                SUM(CASE WHEN status = 'acknowledged' THEN 1 ELSE 0 END) AS acknowledged_count,
                SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) AS resolved_count
            FROM proctor_alerts
            WHERE (? IS NULL OR exam_id = ?)
            GROUP BY exam_id
            ORDER BY total_count DESC, exam_id ASC
            """,
            (exam_id, exam_id),
        ).fetchall()

        total_count = (
            status_counts.get("open", 0)
            + status_counts.get("acknowledged", 0)
            + status_counts.get("resolved", 0)
        )

        return {
            "total_count": total_count,
            "open_count": status_counts.get("open", 0),
            "acknowledged_count": status_counts.get("acknowledged", 0),
            "resolved_count": status_counts.get("resolved", 0),
            "by_indicator": [
                {
                    "indicator_code": row["indicator_code"],
                    "total_count": int(row["total_count"] or 0),
                    "open_count": int(row["open_count"] or 0),
                    "acknowledged_count": int(row["acknowledged_count"] or 0),
                    "resolved_count": int(row["resolved_count"] or 0),
                }
                for row in indicator_rows
            ],
            "by_exam": [
                {
                    "exam_id": row["exam_id"],
                    "total_count": int(row["total_count"] or 0),
                    "open_count": int(row["open_count"] or 0),
                    "acknowledged_count": int(row["acknowledged_count"] or 0),
                    "resolved_count": int(row["resolved_count"] or 0),
                }
                for row in exam_rows
            ],
        }

    def list_alerts_for_metrics(
        self,
        exam_id: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT
                id, attempt_id, exam_id, student_id,
                indicator_code, indicator_payload_json,
                status, detection_count,
                first_detected_at, last_detected_at, created_at,
                acknowledged_at, acknowledged_by,
                resolved_at, resolved_by, resolution_note
            FROM proctor_alerts
            WHERE (? IS NULL OR exam_id = ?)
            ORDER BY created_at DESC, id DESC
            """,
            (exam_id, exam_id),
        ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def acknowledge_alert(
        self,
        alert_id: str,
        actor_id: str,
        acknowledged_at: str,
    ) -> dict[str, Any] | None:
        existing = self.get_alert(alert_id)
        if existing is None:
            return None
        if existing["status"] == "open":
            self._conn.execute(
                """
                UPDATE proctor_alerts
                SET status = 'acknowledged',
                    acknowledged_at = COALESCE(acknowledged_at, ?),
                    acknowledged_by = COALESCE(acknowledged_by, ?)
                WHERE id = ? AND status = 'open'
                """,
                (acknowledged_at, actor_id, alert_id),
            )
        return self.get_alert(alert_id)

    def resolve_alert(
        self,
        alert_id: str,
        actor_id: str,
        resolved_at: str,
        resolution_note: str | None = None,
    ) -> dict[str, Any] | None:
        existing = self.get_alert(alert_id)
        if existing is None:
            return None
        if existing["status"] != "resolved":
            self._conn.execute(
                """
                UPDATE proctor_alerts
                SET status = 'resolved',
                    resolved_at = COALESCE(resolved_at, ?),
                    resolved_by = COALESCE(resolved_by, ?),
                    resolution_note = COALESCE(resolution_note, ?)
                WHERE id = ? AND status IN ('open', 'acknowledged')
                """,
                (resolved_at, actor_id, resolution_note, alert_id),
            )
        return self.get_alert(alert_id)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        try:
            payload = json.loads(row["indicator_payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        return {
            "id": row["id"],
            "attempt_id": row["attempt_id"],
            "exam_id": row["exam_id"],
            "student_id": row["student_id"],
            "indicator_code": row["indicator_code"],
            "indicator_payload": payload,
            "status": row["status"],
            "detection_count": int(row["detection_count"] or 0),
            "first_detected_at": row["first_detected_at"],
            "last_detected_at": row["last_detected_at"],
            "created_at": row["created_at"],
            "acknowledged_at": row["acknowledged_at"],
            "acknowledged_by": row["acknowledged_by"],
            "resolved_at": row["resolved_at"],
            "resolved_by": row["resolved_by"],
            "resolution_note": row["resolution_note"],
        }
