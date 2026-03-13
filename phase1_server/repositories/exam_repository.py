"""Repository for exam persistence and snapshot storage."""

from __future__ import annotations

import sqlite3
from typing import Protocol

from phase1_server.models import AttemptQuestionSnapshot, Exam, ExamStatus


class ExamRepository(Protocol):
    def create_exam(self, exam: Exam) -> None: ...

    def get_exam(self, exam_id: str) -> Exam | None: ...

    def list_exams(self) -> list[Exam]: ...

    def delete_exam(self, exam_id: str) -> None: ...

    def count_attempts(self, exam_id: str) -> int: ...

    def add_questions(self, exam_id: str, question_ids: list[str]) -> None: ...

    def list_question_ids(self, exam_id: str) -> list[str]: ...

    def set_status(self, exam_id: str, status: ExamStatus) -> None: ...

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
                status, published, created_at, passing_percentage
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exam.id,
                exam.name,
                exam.duration_minutes,
                exam.negative_marking,
                exam.status.value,
                1 if exam.published else 0,
                exam.created_at,
                exam.passing_percentage,
            ),
        )

    def get_exam(self, exam_id: str) -> Exam | None:
        row = self._conn.execute(
            """
            SELECT id, name, duration_minutes, negative_marking,
                   status, published, created_at, passing_percentage
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
            passing_percentage=row["passing_percentage"],
        )

    def list_exams(self) -> list[Exam]:
        rows = self._conn.execute(
            """
            SELECT id, name, duration_minutes, negative_marking,
                   status, published, created_at, passing_percentage
            FROM exams
            ORDER BY created_at DESC
            """
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
                passing_percentage=row["passing_percentage"],
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
