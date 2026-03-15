"""Repository for question, option, and text-variant persistence."""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any, Protocol

from phase1_server.models import (
    Option,
    Question,
    QuestionTextVariant,
    QuestionType,
    QuestionVariantDecision,
)


class QuestionRepository(Protocol):
    def create_question(
        self,
        question: Question,
        options: list[Option],
        accepted_answers: list[tuple[str, str, str, str, str, str]] | None = None,
    ) -> None: ...

    def list_questions(
        self,
        owner_admin_id: str | None = None,
        include_all: bool = False,
    ) -> list[tuple[Question, list[Option], list[QuestionTextVariant]]]: ...

    def delete_question(self, question_id: str) -> bool: ...

    def question_exists(self, question_id: str) -> bool: ...

    def get_question(self, question_id: str) -> Question | None: ...

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

    def list_text_variants(
        self,
        question_id: str,
        decision: str | None = None,
    ) -> list[QuestionTextVariant]: ...

    def get_text_variant_by_normalized(
        self,
        question_id: str,
        normalized_answer_text: str,
    ) -> QuestionTextVariant | None: ...

    def upsert_text_variant(
        self,
        question_id: str,
        answer_text: str,
        normalized_answer_text: str,
        decision: str,
        created_by: str,
        created_at: str,
    ) -> str: ...


class SQLiteQuestionRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create_question(
        self,
        question: Question,
        options: list[Option],
        accepted_answers: list[tuple[str, str, str, str, str, str]] | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO questions(
                id, text, topic, difficulty, marks, created_at, owner_admin_id, question_type,
                difficulty_level, discrimination_index, topic_tag, cognitive_level,
                word_target_min, word_target_max, word_hard_max
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question.id,
                question.text,
                question.topic,
                question.difficulty,
                question.marks,
                question.created_at,
                question.owner_admin_id,
                question.question_type.value,
                question.difficulty_level,
                question.discrimination_index,
                question.topic_tag,
                question.cognitive_level,
                question.word_target_min,
                question.word_target_max,
                question.word_hard_max,
            ),
        )
        if options:
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
        if accepted_answers:
            self._conn.executemany(
                """
                INSERT INTO question_text_variants(
                    id, question_id, answer_text, normalized_answer_text, decision, created_by, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        variant_id,
                        question.id,
                        answer_text,
                        normalized_answer_text,
                        decision,
                        created_by,
                        created_at,
                    )
                    for variant_id, answer_text, normalized_answer_text, decision, created_by, created_at in accepted_answers
                ],
            )

    def list_questions(
        self,
        owner_admin_id: str | None = None,
        include_all: bool = False,
    ) -> list[tuple[Question, list[Option], list[QuestionTextVariant]]]:
        if include_all or not owner_admin_id:
            question_rows = self._conn.execute(
                """
                SELECT
                    id, text, topic, difficulty, marks, created_at, owner_admin_id, question_type,
                    difficulty_level, discrimination_index, topic_tag, cognitive_level,
                    word_target_min, word_target_max, word_hard_max
                FROM questions
                ORDER BY created_at DESC
                """
            ).fetchall()
        else:
            question_rows = self._conn.execute(
                """
                SELECT
                    id, text, topic, difficulty, marks, created_at, owner_admin_id, question_type,
                    difficulty_level, discrimination_index, topic_tag, cognitive_level,
                    word_target_min, word_target_max, word_hard_max
                FROM questions
                WHERE owner_admin_id = ?
                ORDER BY created_at DESC
                """,
                (owner_admin_id,),
            ).fetchall()
        option_rows = self._conn.execute(
            """
            SELECT id, question_id, option_text, is_correct
            FROM options
            ORDER BY question_id
            """
        ).fetchall()
        variant_rows = self._conn.execute(
            """
            SELECT id, question_id, answer_text, normalized_answer_text, decision, created_by, created_at
            FROM question_text_variants
            ORDER BY created_at ASC
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

        variant_map: dict[str, list[QuestionTextVariant]] = {}
        for row in variant_rows:
            variant_map.setdefault(row["question_id"], []).append(self._variant_from_row(row))

        result: list[tuple[Question, list[Option], list[QuestionTextVariant]]] = []
        for row in question_rows:
            question = self._question_from_row(row)
            result.append(
                (
                    question,
                    option_map.get(question.id, []),
                    variant_map.get(question.id, []),
                )
            )
        return result

    def delete_question(self, question_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        return cur.rowcount > 0

    def question_exists(self, question_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM questions WHERE id = ? LIMIT 1", (question_id,)
        ).fetchone()
        return row is not None

    def get_question(self, question_id: str) -> Question | None:
        row = self._conn.execute(
            """
            SELECT
                id, text, topic, difficulty, marks, created_at, owner_admin_id, question_type,
                difficulty_level, discrimination_index, topic_tag, cognitive_level,
                word_target_min, word_target_max, word_hard_max
            FROM questions
            WHERE id = ?
            """,
            (question_id,),
        ).fetchone()
        return None if row is None else self._question_from_row(row)

    def get_question_with_options(
        self,
        question_id: str,
    ) -> tuple[Question, list[Option]] | None:
        question = self.get_question(question_id)
        if question is None:
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
            "word_target_min",
            "word_target_max",
            "word_hard_max",
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

    def list_text_variants(
        self,
        question_id: str,
        decision: str | None = None,
    ) -> list[QuestionTextVariant]:
        if decision:
            rows = self._conn.execute(
                """
                SELECT id, question_id, answer_text, normalized_answer_text, decision, created_by, created_at
                FROM question_text_variants
                WHERE question_id = ? AND decision = ?
                ORDER BY created_at ASC
                """,
                (question_id, decision),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT id, question_id, answer_text, normalized_answer_text, decision, created_by, created_at
                FROM question_text_variants
                WHERE question_id = ?
                ORDER BY created_at ASC
                """,
                (question_id,),
            ).fetchall()
        return [self._variant_from_row(row) for row in rows]

    def get_text_variant_by_normalized(
        self,
        question_id: str,
        normalized_answer_text: str,
    ) -> QuestionTextVariant | None:
        row = self._conn.execute(
            """
            SELECT id, question_id, answer_text, normalized_answer_text, decision, created_by, created_at
            FROM question_text_variants
            WHERE question_id = ? AND normalized_answer_text = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (question_id, normalized_answer_text),
        ).fetchone()
        return None if row is None else self._variant_from_row(row)

    def upsert_text_variant(
        self,
        question_id: str,
        answer_text: str,
        normalized_answer_text: str,
        decision: str,
        created_by: str,
        created_at: str,
    ) -> str:
        existing = self.get_text_variant_by_normalized(question_id, normalized_answer_text)
        if existing is not None and existing.decision.value == decision:
            return existing.id
        variant_id = existing.id if existing is not None else self._generate_variant_id()
        if existing is not None:
            self._conn.execute(
                """
                UPDATE question_text_variants
                SET answer_text = ?, decision = ?, created_by = ?, created_at = ?
                WHERE id = ?
                """,
                (answer_text, decision, created_by, created_at, variant_id),
            )
        else:
            self._conn.execute(
                """
                INSERT INTO question_text_variants(
                    id, question_id, answer_text, normalized_answer_text, decision, created_by, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    variant_id,
                    question_id,
                    answer_text,
                    normalized_answer_text,
                    decision,
                    created_by,
                    created_at,
                ),
            )
        return variant_id

    def _question_from_row(self, row: sqlite3.Row) -> Question:
        return Question(
            id=row["id"],
            text=row["text"],
            topic=row["topic"],
            difficulty=row["difficulty"],
            marks=row["marks"],
            created_at=row["created_at"],
            owner_admin_id=row["owner_admin_id"],
            question_type=QuestionType(row["question_type"] or QuestionType.MCQ_SINGLE.value),
            difficulty_level=row["difficulty_level"],
            discrimination_index=row["discrimination_index"],
            topic_tag=row["topic_tag"],
            cognitive_level=row["cognitive_level"],
            word_target_min=row["word_target_min"],
            word_target_max=row["word_target_max"],
            word_hard_max=row["word_hard_max"],
        )

    def _variant_from_row(self, row: sqlite3.Row) -> QuestionTextVariant:
        return QuestionTextVariant(
            id=row["id"],
            question_id=row["question_id"],
            answer_text=row["answer_text"],
            normalized_answer_text=row["normalized_answer_text"],
            decision=QuestionVariantDecision(row["decision"]),
            created_by=row["created_by"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _generate_variant_id() -> str:
        return str(uuid.uuid4())
