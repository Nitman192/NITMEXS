"""Repository for institutional analytics storage and queries."""

from __future__ import annotations

import sqlite3
from typing import Protocol


class AnalyticsRepository(Protocol):
    def upsert_item_stat(
        self,
        exam_id: str,
        question_id: str,
        is_correct: bool,
        marks_awarded: float,
    ) -> None: ...

    def get_exam_item_statistics(self, exam_id: str) -> list[dict]: ...

    def get_exam_summary(self, exam_id: str) -> dict: ...

    def get_student_performance(self, student_id: str) -> dict: ...


class SQLiteAnalyticsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def upsert_item_stat(
        self,
        exam_id: str,
        question_id: str,
        is_correct: bool,
        marks_awarded: float,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO item_statistics(
                exam_id, question_id, attempts_count, correct_count, total_marks_awarded
            ) VALUES(?, ?, 1, ?, ?)
            ON CONFLICT(exam_id, question_id)
            DO UPDATE SET
                attempts_count = item_statistics.attempts_count + 1,
                correct_count = item_statistics.correct_count + excluded.correct_count,
                total_marks_awarded = item_statistics.total_marks_awarded + excluded.total_marks_awarded
            """,
            (
                exam_id,
                question_id,
                1 if is_correct else 0,
                marks_awarded,
            ),
        )

    def get_exam_item_statistics(self, exam_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT question_id, attempts_count, correct_count, total_marks_awarded
            FROM item_statistics
            WHERE exam_id = ?
            ORDER BY question_id ASC
            """,
            (exam_id,),
        ).fetchall()

        result: list[dict] = []
        for row in rows:
            attempts = int(row["attempts_count"])
            correct = int(row["correct_count"])
            total_marks = float(row["total_marks_awarded"])
            result.append(
                {
                    "question_id": row["question_id"],
                    "total_attempts": attempts,
                    "difficulty_index": (correct / attempts) * 100.0 if attempts else 0.0,
                    "average_score": (total_marks / attempts) if attempts else 0.0,
                }
            )
        return result

    def get_exam_summary(self, exam_id: str) -> dict:
        row = self._conn.execute(
            """
            SELECT
                COUNT(*) AS total_attempts,
                AVG(ar.total_score) AS mean_score,
                SUM(CASE WHEN ar.passed = 1 THEN 1 ELSE 0 END) AS pass_count
            FROM attempt_results ar
            INNER JOIN attempts a ON a.id = ar.attempt_id
            WHERE a.exam_id = ?
            """,
            (exam_id,),
        ).fetchone()
        total_attempts = int(row["total_attempts"] or 0)
        pass_count = int(row["pass_count"] or 0)
        return {
            "total_attempts": total_attempts,
            "mean_score": float(row["mean_score"] or 0.0),
            "pass_rate": ((pass_count / total_attempts) * 100.0) if total_attempts else 0.0,
        }

    def get_student_performance(self, student_id: str) -> dict:
        rows = self._conn.execute(
            """
            SELECT a.exam_id, ar.total_score, ar.percentage, ar.passed, ar.graded_at
            FROM attempt_results ar
            INNER JOIN attempts a ON a.id = ar.attempt_id
            WHERE a.candidate_id = ?
            ORDER BY ar.graded_at DESC
            """,
            (student_id,),
        ).fetchall()

        attempts = [
            {
                "exam_id": row["exam_id"],
                "total_score": float(row["total_score"]),
                "percentage": float(row["percentage"]),
                "passed": bool(row["passed"]),
                "graded_at": row["graded_at"],
            }
            for row in rows
        ]

        total = len(attempts)
        passed = sum(1 for item in attempts if item["passed"])
        avg_percentage = (
            sum(item["percentage"] for item in attempts) / total if total else 0.0
        )
        return {
            "student_id": student_id,
            "total_attempts": total,
            "passed_attempts": passed,
            "pass_rate": ((passed / total) * 100.0) if total else 0.0,
            "average_percentage": avg_percentage,
            "attempts": attempts,
        }
