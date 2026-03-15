"""Repository for exam persistence and snapshot storage."""

from __future__ import annotations

import json
import sqlite3
from typing import Protocol

from phase1_server.models import AttemptQuestionSnapshot, Exam, ExamStatus


class ExamRepository(Protocol):
    def create_exam(self, exam: Exam) -> None: ...

    def get_exam(self, exam_id: str) -> Exam | None: ...

    def list_exams(
        self,
        owner_admin_id: str | None = None,
        include_all: bool = False,
    ) -> list[Exam]: ...

    def delete_exam(self, exam_id: str) -> None: ...

    def count_attempts(self, exam_id: str) -> int: ...

    def add_questions(self, exam_id: str, question_ids: list[str]) -> None: ...

    def list_question_ids(self, exam_id: str) -> list[str]: ...

    def set_status(self, exam_id: str, status: ExamStatus) -> None: ...

    def set_reference_exam(self, exam_id: str, reference_exam_id: str | None) -> None: ...

    def set_custom_rules(self, exam_id: str, custom_rules: list[str]) -> None: ...

    def clear_snapshot(self, attempt_id: str) -> None: ...

    def store_snapshot(self, items: list[AttemptQuestionSnapshot]) -> None: ...

    def log_exam_event(
        self,
        exam_id: str,
        event_type: str,
        timestamp: str,
        actor_id: str,
        actor_role: str,
    ) -> None: ...


class SQLiteExamRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create_exam(self, exam: Exam) -> None:
        self._conn.execute(
            """
            INSERT INTO exams(
                id, name, duration_minutes, negative_marking,
                status, published, created_at, owner_admin_id, passing_percentage, reference_exam_id, custom_rules_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exam.id,
                exam.name,
                exam.duration_minutes,
                exam.negative_marking,
                exam.status.value,
                1 if exam.published else 0,
                exam.created_at,
                exam.owner_admin_id,
                exam.passing_percentage,
                exam.reference_exam_id,
                json.dumps(exam.custom_rules or []),
            ),
        )

    def get_exam(self, exam_id: str) -> Exam | None:
        row = self._conn.execute(
            """
            SELECT id, name, duration_minutes, negative_marking,
                   status, published, created_at, owner_admin_id, passing_percentage, reference_exam_id, custom_rules_json
            FROM exams
            WHERE id = ?
            """,
            (exam_id,),
        ).fetchone()
        if row is None:
            return None
        return Exam(
            id=row["id"],
            name=row["name"],
            duration_minutes=row["duration_minutes"],
            negative_marking=row["negative_marking"],
            status=ExamStatus(row["status"]),
            published=bool(row["published"]),
            created_at=row["created_at"],
            owner_admin_id=row["owner_admin_id"],
            passing_percentage=row["passing_percentage"],
            reference_exam_id=row["reference_exam_id"],
            custom_rules=self._parse_rules(row["custom_rules_json"]),
        )

    def list_exams(
        self,
        owner_admin_id: str | None = None,
        include_all: bool = False,
    ) -> list[Exam]:
        if include_all or not owner_admin_id:
            rows = self._conn.execute(
                """
                SELECT id, name, duration_minutes, negative_marking,
                       status, published, created_at, owner_admin_id, passing_percentage, reference_exam_id, custom_rules_json
                FROM exams
                ORDER BY created_at DESC
                """
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, name, duration_minutes, negative_marking,
                       status, published, created_at, owner_admin_id, passing_percentage, reference_exam_id, custom_rules_json
                FROM exams
                WHERE owner_admin_id = ?
                ORDER BY created_at DESC
                """,
                (owner_admin_id,),
            ).fetchall()
        return [
            Exam(
                id=row["id"],
                name=row["name"],
                duration_minutes=row["duration_minutes"],
                negative_marking=row["negative_marking"],
                status=ExamStatus(row["status"]),
                published=bool(row["published"]),
                created_at=row["created_at"],
                owner_admin_id=row["owner_admin_id"],
                passing_percentage=row["passing_percentage"],
                reference_exam_id=row["reference_exam_id"],
                custom_rules=self._parse_rules(row["custom_rules_json"]),
            )
            for row in rows
        ]

    def delete_exam(self, exam_id: str) -> None:
        self._conn.execute("DELETE FROM exams WHERE id = ?", (exam_id,))

    def count_attempts(self, exam_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS total FROM attempts WHERE exam_id = ?",
            (exam_id,),
        ).fetchone()
        return 0 if row is None else int(row["total"] or 0)

    def add_questions(self, exam_id: str, question_ids: list[str]) -> None:
        self._conn.executemany(
            """
            INSERT OR IGNORE INTO exam_questions(exam_id, question_id)
            VALUES(?, ?)
            """,
            [(exam_id, question_id) for question_id in question_ids],
        )

    def list_question_ids(self, exam_id: str) -> list[str]:
        rows = self._conn.execute(
            "SELECT question_id FROM exam_questions WHERE exam_id = ?", (exam_id,)
        ).fetchall()
        return [row["question_id"] for row in rows]

    def set_status(self, exam_id: str, status: ExamStatus) -> None:
        self._conn.execute(
            "UPDATE exams SET status = ?, published = ? WHERE id = ?",
            (status.value, 1 if status is ExamStatus.ACTIVE else 0, exam_id),
        )

    def set_reference_exam(self, exam_id: str, reference_exam_id: str | None) -> None:
        self._conn.execute(
            "UPDATE exams SET reference_exam_id = ? WHERE id = ?",
            (reference_exam_id, exam_id),
        )

    def set_custom_rules(self, exam_id: str, custom_rules: list[str]) -> None:
        self._conn.execute(
            "UPDATE exams SET custom_rules_json = ? WHERE id = ?",
            (json.dumps(custom_rules or []), exam_id),
        )

    def clear_snapshot(self, attempt_id: str) -> None:
        self._conn.execute(
            "DELETE FROM attempt_question_snapshots WHERE attempt_id = ?",
            (attempt_id,),
        )

    def store_snapshot(self, items: list[AttemptQuestionSnapshot]) -> None:
        self._conn.executemany(
            """
            INSERT INTO attempt_question_snapshots(
                attempt_id, exam_id, question_id, order_index, created_at
            ) VALUES(?, ?, ?, ?, ?)
            """,
            [
                (
                    item.attempt_id,
                    item.exam_id,
                    item.question_id,
                    item.order_index,
                    item.created_at,
                )
                for item in items
            ],
        )

    def log_exam_event(
        self,
        exam_id: str,
        event_type: str,
        timestamp: str,
        actor_id: str,
        actor_role: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO exam_audit_logs(id, exam_id, event_type, timestamp, actor_id, actor_role)
            VALUES(hex(randomblob(16)), ?, ?, ?, ?, ?)
            """,
            (exam_id, event_type, timestamp, actor_id, actor_role),
        )

    @staticmethod
    def _parse_rules(raw: str | None) -> list[str]:
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        return [str(item).strip() for item in data if str(item).strip()]
