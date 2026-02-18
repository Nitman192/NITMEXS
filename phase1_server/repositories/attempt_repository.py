"""Repository for attempt persistence."""

from __future__ import annotations

import sqlite3
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
    ) -> None: ...

    def get_by_candidate_and_exam(self, candidate_id: str, exam_id: str) -> Attempt | None: ...

    def get_snapshot_question_id(self, attempt_id: str, order_index: int) -> str | None: ...

    def question_in_snapshot(self, attempt_id: str, question_id: str) -> bool: ...

    def upsert_response(self, response: AttemptResponse) -> None: ...


class SQLiteAttemptRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get(self, attempt_id: str) -> Attempt | None:
        row = self._conn.execute(
            """
            SELECT id, candidate_id, exam_id, status, created_at, updated_at, submitted_at
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
            submitted_at=row["submitted_at"],
        )

    def create(self, attempt: Attempt) -> None:
        self._conn.execute(
            """
            INSERT INTO attempts(id, candidate_id, exam_id, status, created_at, updated_at, submitted_at)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt.id,
                attempt.candidate_id,
                attempt.exam_id,
                attempt.status.value,
                attempt.created_at,
                attempt.updated_at,
                attempt.submitted_at,
            ),
        )

    def update_status(
        self,
        attempt_id: str,
        status: AttemptStatus,
        updated_at: str,
        submitted_at: str | None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE attempts
            SET status = ?, updated_at = ?, submitted_at = COALESCE(?, submitted_at)
            WHERE id = ?
            """,
            (status.value, updated_at, submitted_at, attempt_id),
        )

    def get_by_candidate_and_exam(self, candidate_id: str, exam_id: str) -> Attempt | None:
        row = self._conn.execute(
            """
            SELECT id, candidate_id, exam_id, status, created_at, updated_at, submitted_at
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
            submitted_at=row["submitted_at"],
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
