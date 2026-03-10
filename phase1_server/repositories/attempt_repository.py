"""Repository for attempt persistence."""

from __future__ import annotations

import sqlite3
import uuid
from typing import Protocol

from phase1_server.models import Attempt, AttemptResponse, AttemptStatus


class AttemptRepository(Protocol):
    def get(self, attempt_id: str) -> Attempt | None: ...

    def create(self, attempt: Attempt) -> None: ...

    def update_status(
        self,
        attempt_id: str,
        status: AttemptStatus,
        updated_at: str,
        submitted_at: str | None,
        expected_version: int,
    ) -> bool: ...

    def get_by_candidate_and_exam(
        self,
        candidate_id: str,
        exam_id: str,
    ) -> Attempt | None: ...

    def get_snapshot_question_id(self, attempt_id: str, order_index: int) -> str | None: ...

    def list_snapshot_question_ids(self, attempt_id: str) -> list[str]: ...

    def question_in_snapshot(self, attempt_id: str, question_id: str) -> bool: ...

    def upsert_response(self, response: AttemptResponse) -> None: ...

    def get_responses(self, attempt_id: str) -> dict[str, str]: ...

    def clear_results(self, attempt_id: str) -> None: ...

    def save_attempt_result(
        self,
        attempt_id: str,
        total_score: float,
        total_possible_marks: float,
        percentage: float,
        passed: bool,
        graded_at: str,
    ) -> None: ...

    def save_question_result(
        self,
        attempt_id: str,
        question_id: str,
        selected_option_id: str | None,
        correct_option_id: str,
        marks_awarded: float,
        max_marks: float,
        is_correct: bool,
    ) -> None: ...

    def get_attempt_result(self, attempt_id: str) -> dict | None: ...

    def result_exists(self, attempt_id: str) -> bool: ...

    def get_question_results(self, attempt_id: str) -> list[dict]: ...

    def log_audit_event(
        self,
        attempt_id: str,
        event_type: str,
        timestamp: str,
        actor_id: str,
        actor_role: str,
    ) -> None: ...

    def list_audit_events(self, attempt_id: str) -> list[dict]: ...

    def is_expired(self, attempt_id: str, now_iso: str) -> bool: ...

    def get_exam_question_analytics(self, exam_id: str) -> list[dict]: ...

    def get_exam_attempt_scores(self, exam_id: str) -> list[dict]: ...


class SQLiteAttemptRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get(self, attempt_id: str) -> Attempt | None:
        row = self._conn.execute(
            """
            SELECT id, candidate_id, exam_id, status, created_at, updated_at, version, submitted_at, expires_at
            FROM attempts
            WHERE id = ?
            """,
            (attempt_id,),
        ).fetchone()
        if not row:
            return None
        return Attempt(
            id=row["id"],
            candidate_id=row["candidate_id"],
            exam_id=row["exam_id"],
            status=AttemptStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=row["version"],
            submitted_at=row["submitted_at"],
            expires_at=row["expires_at"],
        )

    def create(self, attempt: Attempt) -> None:
        self._conn.execute(
            """
            INSERT INTO attempts(
                id, candidate_id, exam_id, status, created_at, updated_at, version, submitted_at, expires_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt.id,
                attempt.candidate_id,
                attempt.exam_id,
                attempt.status.value,
                attempt.created_at,
                attempt.updated_at,
                attempt.version,
                attempt.submitted_at,
                attempt.expires_at,
            ),
        )

    def update_status(
        self,
        attempt_id: str,
        status: AttemptStatus,
        updated_at: str,
        submitted_at: str | None,
        expected_version: int,
    ) -> bool:
        cursor = self._conn.execute(
            """
            UPDATE attempts
            SET status = ?,
                updated_at = ?,
                submitted_at = COALESCE(?, submitted_at),
                version = version + 1
            WHERE id = ? AND version = ?
            """,
            (status.value, updated_at, submitted_at, attempt_id, expected_version),
        )
        return cursor.rowcount == 1

    def get_by_candidate_and_exam(
        self,
        candidate_id: str,
        exam_id: str,
    ) -> Attempt | None:
        row = self._conn.execute(
            """
            SELECT id, candidate_id, exam_id, status, created_at, updated_at, version, submitted_at, expires_at
            FROM attempts
            WHERE candidate_id = ? AND exam_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (candidate_id, exam_id),
        ).fetchone()
        if not row:
            return None
        return Attempt(
            id=row["id"],
            candidate_id=row["candidate_id"],
            exam_id=row["exam_id"],
            status=AttemptStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=row["version"],
            submitted_at=row["submitted_at"],
            expires_at=row["expires_at"],
        )

    def get_snapshot_question_id(self, attempt_id: str, order_index: int) -> str | None:
        row = self._conn.execute(
            """
            SELECT question_id
            FROM attempt_question_snapshots
            WHERE attempt_id = ? AND order_index = ?
            """,
            (attempt_id, order_index),
        ).fetchone()
        return None if row is None else row["question_id"]

    def list_snapshot_question_ids(self, attempt_id: str) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT question_id
            FROM attempt_question_snapshots
            WHERE attempt_id = ?
            ORDER BY order_index ASC
            """,
            (attempt_id,),
        ).fetchall()
        return [row["question_id"] for row in rows]

    def question_in_snapshot(self, attempt_id: str, question_id: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1
            FROM attempt_question_snapshots
            WHERE attempt_id = ? AND question_id = ?
            LIMIT 1
            """,
            (attempt_id, question_id),
        ).fetchone()
        return row is not None

    def upsert_response(self, response: AttemptResponse) -> None:
        self._conn.execute(
            """
            INSERT INTO attempt_responses(attempt_id, question_id, selected_option_id, answered_at)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(attempt_id, question_id)
            DO UPDATE SET selected_option_id = excluded.selected_option_id,
                          answered_at = excluded.answered_at
            """,
            (
                response.attempt_id,
                response.question_id,
                response.selected_option_id,
                response.answered_at,
            ),
        )

    def get_responses(self, attempt_id: str) -> dict[str, str]:
        rows = self._conn.execute(
            """
            SELECT question_id, selected_option_id
            FROM attempt_responses
            WHERE attempt_id = ?
            """,
            (attempt_id,),
        ).fetchall()
        return {row["question_id"]: row["selected_option_id"] for row in rows}

    def clear_results(self, attempt_id: str) -> None:
        self._conn.execute(
            "DELETE FROM attempt_question_results WHERE attempt_id = ?",
            (attempt_id,),
        )
        self._conn.execute(
            "DELETE FROM attempt_results WHERE attempt_id = ?",
            (attempt_id,),
        )

    def save_attempt_result(
        self,
        attempt_id: str,
        total_score: float,
        total_possible_marks: float,
        percentage: float,
        passed: bool,
        graded_at: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO attempt_results(
                attempt_id, total_score, total_possible_marks, percentage, passed, graded_at
            ) VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                total_score,
                total_possible_marks,
                percentage,
                1 if passed else 0,
                graded_at,
            ),
        )

    def save_question_result(
        self,
        attempt_id: str,
        question_id: str,
        selected_option_id: str | None,
        correct_option_id: str,
        marks_awarded: float,
        max_marks: float,
        is_correct: bool,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO attempt_question_results(
                attempt_id, question_id, selected_option_id, correct_option_id,
                marks_awarded, max_marks, is_correct
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                question_id,
                selected_option_id,
                correct_option_id,
                marks_awarded,
                max_marks,
                1 if is_correct else 0,
            ),
        )

    def get_attempt_result(self, attempt_id: str) -> dict | None:
        row = self._conn.execute(
            """
            SELECT attempt_id, total_score, total_possible_marks, percentage, passed, graded_at
            FROM attempt_results
            WHERE attempt_id = ?
            """,
            (attempt_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "attempt_id": row["attempt_id"],
            "total_score": row["total_score"],
            "total_possible_marks": row["total_possible_marks"],
            "percentage": row["percentage"],
            "passed": bool(row["passed"]),
            "graded_at": row["graded_at"],
        }

    def result_exists(self, attempt_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM attempt_results WHERE attempt_id = ? LIMIT 1",
            (attempt_id,),
        ).fetchone()
        return row is not None

    def get_question_results(self, attempt_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT attempt_id, question_id, selected_option_id, correct_option_id,
                   marks_awarded, max_marks, is_correct
            FROM attempt_question_results
            WHERE attempt_id = ?
            ORDER BY question_id ASC
            """,
            (attempt_id,),
        ).fetchall()
        return [
            {
                "attempt_id": row["attempt_id"],
                "question_id": row["question_id"],
                "selected_option_id": row["selected_option_id"],
                "correct_option_id": row["correct_option_id"],
                "marks_awarded": row["marks_awarded"],
                "max_marks": row["max_marks"],
                "is_correct": bool(row["is_correct"]),
            }
            for row in rows
        ]

    def log_audit_event(
        self,
        attempt_id: str,
        event_type: str,
        timestamp: str,
        actor_id: str,
        actor_role: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO audit_logs(id, attempt_id, event_type, timestamp, actor_id, actor_role)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), attempt_id, event_type, timestamp, actor_id, actor_role),
        )

    def list_audit_events(self, attempt_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT id, attempt_id, event_type, timestamp, actor_id, actor_role
            FROM audit_logs
            WHERE attempt_id = ?
            ORDER BY timestamp ASC
            """,
            (attempt_id,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "attempt_id": row["attempt_id"],
                "event_type": row["event_type"],
                "timestamp": row["timestamp"],
                "actor_id": row["actor_id"],
                "actor_role": row["actor_role"],
            }
            for row in rows
        ]

    def is_expired(self, attempt_id: str, now_iso: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1
            FROM attempts
            WHERE id = ? AND expires_at IS NOT NULL AND expires_at < ?
            LIMIT 1
            """,
            (attempt_id, now_iso),
        ).fetchone()
        return row is not None


    def get_exam_question_analytics(self, exam_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT
                aqr.question_id AS question_id,
                COUNT(*) AS total_attempts,
                SUM(CASE WHEN aqr.is_correct = 1 THEN 1 ELSE 0 END) AS correct_count,
                AVG(aqr.marks_awarded) AS average_score
            FROM attempt_question_results aqr
            INNER JOIN attempts a ON a.id = aqr.attempt_id
            WHERE a.exam_id = ?
            GROUP BY aqr.question_id
            ORDER BY aqr.question_id ASC
            """,
            (exam_id,),
        ).fetchall()
        result = []
        for row in rows:
            total_attempts = int(row["total_attempts"])
            correct_count = int(row["correct_count"] or 0)
            difficulty_index = (
                (correct_count / total_attempts) * 100.0 if total_attempts > 0 else 0.0
            )
            result.append(
                {
                    "question_id": row["question_id"],
                    "total_attempts": total_attempts,
                    "average_score": float(row["average_score"] or 0.0),
                    "difficulty_index": difficulty_index,
                }
            )
        return result

    def get_exam_attempt_scores(self, exam_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT ar.attempt_id, ar.total_score, ar.passed
            FROM attempt_results ar
            INNER JOIN attempts a ON a.id = ar.attempt_id
            WHERE a.exam_id = ?
            ORDER BY ar.attempt_id ASC
            """,
            (exam_id,),
        ).fetchall()
        return [
            {
                "attempt_id": row["attempt_id"],
                "total_score": float(row["total_score"]),
                "passed": bool(row["passed"]),
            }
            for row in rows
        ]
