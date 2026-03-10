"""Repository for question recalibration run history and rollback snapshots."""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any, Protocol


class QuestionRecalibrationRepository(Protocol):
    def create_run(
        self,
        run_id: str,
        exam_id: str,
        mode: str,
        min_attempts: int | None,
        total_questions: int,
        eligible_questions: int,
        updated_questions: int,
        skipped_questions: int,
        triggered_by: str,
        created_at: str,
        source_run_id: str | None = None,
    ) -> None: ...

    def create_run_items(
        self,
        run_id: str,
        items: list[dict[str, Any]],
        created_at: str,
    ) -> None: ...

    def list_runs_by_exam(self, exam_id: str, limit: int = 50) -> list[dict[str, Any]]: ...

    def get_run(self, run_id: str) -> dict[str, Any] | None: ...

    def list_run_items(self, run_id: str) -> list[dict[str, Any]]: ...


class SQLiteQuestionRecalibrationRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create_run(
        self,
        run_id: str,
        exam_id: str,
        mode: str,
        min_attempts: int | None,
        total_questions: int,
        eligible_questions: int,
        updated_questions: int,
        skipped_questions: int,
        triggered_by: str,
        created_at: str,
        source_run_id: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO question_recalibration_runs(
                id, exam_id, mode, min_attempts, total_questions,
                eligible_questions, updated_questions, skipped_questions,
                triggered_by, source_run_id, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                exam_id,
                mode,
                min_attempts,
                total_questions,
                eligible_questions,
                updated_questions,
                skipped_questions,
                triggered_by,
                source_run_id,
                created_at,
            ),
        )

    def create_run_items(
        self,
        run_id: str,
        items: list[dict[str, Any]],
        created_at: str,
    ) -> None:
        self._conn.executemany(
            """
            INSERT INTO question_recalibration_items(
                id, run_id, question_id, total_attempts,
                observed_difficulty_index,
                previous_difficulty, previous_difficulty_level, previous_discrimination_index,
                suggested_difficulty, suggested_difficulty_level, suggested_discrimination_index,
                applied, status, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    str(uuid.uuid4()),
                    run_id,
                    item["question_id"],
                    int(item.get("total_attempts") or 0),
                    item.get("observed_difficulty_index"),
                    item.get("previous_difficulty"),
                    item.get("previous_difficulty_level"),
                    item.get("previous_discrimination_index"),
                    item.get("suggested_difficulty"),
                    item.get("suggested_difficulty_level"),
                    item.get("suggested_discrimination_index"),
                    1 if item.get("applied") else 0,
                    item.get("status") or "unknown",
                    created_at,
                )
                for item in items
            ],
        )

    def list_runs_by_exam(self, exam_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT
                id, exam_id, mode, min_attempts, total_questions, eligible_questions,
                updated_questions, skipped_questions, triggered_by, source_run_id, created_at
            FROM question_recalibration_runs
            WHERE exam_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (exam_id, limit),
        ).fetchall()
        return [
            {
                "run_id": row["id"],
                "exam_id": row["exam_id"],
                "mode": row["mode"],
                "min_attempts": row["min_attempts"],
                "total_questions": int(row["total_questions"]),
                "eligible_questions": int(row["eligible_questions"]),
                "updated_questions": int(row["updated_questions"]),
                "skipped_questions": int(row["skipped_questions"]),
                "triggered_by": row["triggered_by"],
                "source_run_id": row["source_run_id"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT
                id, exam_id, mode, min_attempts, total_questions, eligible_questions,
                updated_questions, skipped_questions, triggered_by, source_run_id, created_at
            FROM question_recalibration_runs
            WHERE id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "run_id": row["id"],
            "exam_id": row["exam_id"],
            "mode": row["mode"],
            "min_attempts": row["min_attempts"],
            "total_questions": int(row["total_questions"]),
            "eligible_questions": int(row["eligible_questions"]),
            "updated_questions": int(row["updated_questions"]),
            "skipped_questions": int(row["skipped_questions"]),
            "triggered_by": row["triggered_by"],
            "source_run_id": row["source_run_id"],
            "created_at": row["created_at"],
        }

    def list_run_items(self, run_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT
                question_id, total_attempts, observed_difficulty_index,
                previous_difficulty, previous_difficulty_level, previous_discrimination_index,
                suggested_difficulty, suggested_difficulty_level, suggested_discrimination_index,
                applied, status, created_at
            FROM question_recalibration_items
            WHERE run_id = ?
            ORDER BY question_id ASC
            """,
            (run_id,),
        ).fetchall()
        return [
            {
                "question_id": row["question_id"],
                "total_attempts": int(row["total_attempts"]),
                "observed_difficulty_index": row["observed_difficulty_index"],
                "previous_difficulty": row["previous_difficulty"],
                "previous_difficulty_level": row["previous_difficulty_level"],
                "previous_discrimination_index": row["previous_discrimination_index"],
                "suggested_difficulty": row["suggested_difficulty"],
                "suggested_difficulty_level": row["suggested_difficulty_level"],
                "suggested_discrimination_index": row["suggested_discrimination_index"],
                "applied": bool(row["applied"]),
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
