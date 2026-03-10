"""Repository for question and option persistence."""

from __future__ import annotations

import sqlite3
from typing import Any, Protocol

from phase1_server.models import Option, Question


class QuestionRepository(Protocol):
    def create_question(self, question: Question, options: list[Option]) -> None: ...

    def list_questions(self) -> list[tuple[Question, list[Option]]]: ...

    def delete_question(self, question_id: str) -> bool: ...

    def question_exists(self, question_id: str) -> bool: ...

    def get_question_with_options(
        self,
        question_id: str,
    ) -> tuple[Question, list[Option]] | None: ...

    def option_belongs_to_question(self, question_id: str, option_id: str) -> bool: ...

    def get_question_marks(self, question_id: str) -> float | None: ...

    def get_correct_option_id(self, question_id: str) -> str | None: ...

    def update_question_metadata(
        self,
        question_id: str,
        changes: dict[str, Any],
    ) -> bool: ...

    def list_usage_statistics(self) -> list[dict[str, Any]]: ...


class SQLiteQuestionRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create_question(self, question: Question, options: list[Option]) -> None:
        self._conn.execute(
            """
            INSERT INTO questions(
                id, text, topic, difficulty, marks, created_at,
                difficulty_level, discrimination_index, topic_tag, cognitive_level
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question.id,
                question.text,
                question.topic,
                question.difficulty,
                question.marks,
                question.created_at,
                question.difficulty_level,
                question.discrimination_index,
                question.topic_tag,
                question.cognitive_level,
            ),
        )
        self._conn.executemany(
            """
            INSERT INTO options(id, question_id, option_text, is_correct)
            VALUES(?, ?, ?, ?)
            """,
            [
                (
                    option.id,
                    option.question_id,
                    option.option_text,
                    1 if option.is_correct else 0,
                )
                for option in options
            ],
        )

    def list_questions(self) -> list[tuple[Question, list[Option]]]:
        question_rows = self._conn.execute(
            """
            SELECT
                id, text, topic, difficulty, marks, created_at,
                difficulty_level, discrimination_index, topic_tag, cognitive_level
            FROM questions
            ORDER BY created_at DESC
            """
        ).fetchall()
        option_rows = self._conn.execute(
            """
            SELECT id, question_id, option_text, is_correct
            FROM options
            ORDER BY question_id
            """
        ).fetchall()

        option_map: dict[str, list[Option]] = {}
        for row in option_rows:
            option_map.setdefault(row["question_id"], []).append(
                Option(
                    id=row["id"],
                    question_id=row["question_id"],
                    option_text=row["option_text"],
                    is_correct=bool(row["is_correct"]),
                )
            )

        result: list[tuple[Question, list[Option]]] = []
        for row in question_rows:
            question = Question(
                id=row["id"],
                text=row["text"],
                topic=row["topic"],
                difficulty=row["difficulty"],
                marks=row["marks"],
                created_at=row["created_at"],
                difficulty_level=row["difficulty_level"],
                discrimination_index=row["discrimination_index"],
                topic_tag=row["topic_tag"],
                cognitive_level=row["cognitive_level"],
            )
            result.append((question, option_map.get(question.id, [])))
        return result

    def delete_question(self, question_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        return cur.rowcount > 0

    def question_exists(self, question_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM questions WHERE id = ? LIMIT 1", (question_id,)
        ).fetchone()
        return row is not None

    def get_question_with_options(
        self,
        question_id: str,
    ) -> tuple[Question, list[Option]] | None:
        question_row = self._conn.execute(
            """
            SELECT
                id, text, topic, difficulty, marks, created_at,
                difficulty_level, discrimination_index, topic_tag, cognitive_level
            FROM questions
            WHERE id = ?
            """,
            (question_id,),
        ).fetchone()
        if question_row is None:
            return None

        option_rows = self._conn.execute(
            """
            SELECT id, question_id, option_text, is_correct
            FROM options
            WHERE question_id = ?
            ORDER BY id
            """,
            (question_id,),
        ).fetchall()

        question = Question(
            id=question_row["id"],
            text=question_row["text"],
            topic=question_row["topic"],
            difficulty=question_row["difficulty"],
            marks=question_row["marks"],
            created_at=question_row["created_at"],
            difficulty_level=question_row["difficulty_level"],
            discrimination_index=question_row["discrimination_index"],
            topic_tag=question_row["topic_tag"],
            cognitive_level=question_row["cognitive_level"],
        )
        options = [
            Option(
                id=row["id"],
                question_id=row["question_id"],
                option_text=row["option_text"],
                is_correct=bool(row["is_correct"]),
            )
            for row in option_rows
        ]
        return question, options

    def option_belongs_to_question(self, question_id: str, option_id: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1
            FROM options
            WHERE id = ? AND question_id = ?
            LIMIT 1
            """,
            (option_id, question_id),
        ).fetchone()
        return row is not None

    def get_question_marks(self, question_id: str) -> float | None:
        row = self._conn.execute(
            "SELECT marks FROM questions WHERE id = ?",
            (question_id,),
        ).fetchone()
        return None if row is None else row["marks"]

    def get_correct_option_id(self, question_id: str) -> str | None:
        row = self._conn.execute(
            """
            SELECT id
            FROM options
            WHERE question_id = ? AND is_correct = 1
            LIMIT 1
            """,
            (question_id,),
        ).fetchone()
        return None if row is None else row["id"]

    def update_question_metadata(
        self,
        question_id: str,
        changes: dict[str, Any],
    ) -> bool:
        allowed_columns = {
            "difficulty",
            "difficulty_level",
            "discrimination_index",
            "topic_tag",
            "cognitive_level",
        }
        assignments: list[str] = []
        values: list[Any] = []

        for key, value in changes.items():
            if key not in allowed_columns:
                continue
            assignments.append(f"{key} = ?")
            values.append(value)

        if not assignments:
            return False

        values.append(question_id)
        cursor = self._conn.execute(
            f"""
            UPDATE questions
            SET {", ".join(assignments)}
            WHERE id = ?
            """,
            tuple(values),
        )
        return cursor.rowcount > 0

    def list_usage_statistics(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT
                q.id AS question_id,
                q.topic AS topic,
                q.topic_tag AS topic_tag,
                q.cognitive_level AS cognitive_level,
                q.difficulty AS difficulty,
                q.difficulty_level AS difficulty_level,
                COUNT(aqr.attempt_id) AS usage_count,
                SUM(CASE WHEN aqr.is_correct = 1 THEN 1 ELSE 0 END) AS correct_count
            FROM questions q
            LEFT JOIN attempt_question_results aqr
                ON aqr.question_id = q.id
            GROUP BY
                q.id, q.topic, q.topic_tag, q.cognitive_level, q.difficulty, q.difficulty_level
            ORDER BY q.created_at DESC
            """
        ).fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            usage_count = int(row["usage_count"] or 0)
            correct_count = int(row["correct_count"] or 0)
            result.append(
                {
                    "question_id": row["question_id"],
                    "topic": row["topic"],
                    "topic_tag": row["topic_tag"],
                    "cognitive_level": row["cognitive_level"],
                    "difficulty": row["difficulty"],
                    "difficulty_level": row["difficulty_level"],
                    "usage_count": usage_count,
                    "correct_count": correct_count,
                    "correct_rate": (
                        (correct_count / usage_count) * 100.0 if usage_count > 0 else 0.0
                    ),
                }
            )
        return result
