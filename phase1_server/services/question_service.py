"""Business logic for question management."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from phase1_server.models import Option, Question, utc_now_iso
from phase1_server.repositories.question_repository import QuestionRepository


class QuestionNotFoundError(ValueError):
    pass


class QuestionValidationError(ValueError):
    pass


@dataclass(frozen=True)
class QuestionCreatePayload:
    text: str
    topic: str
    difficulty: str
    marks: float
    options: list[tuple[str, bool]]
    difficulty_level: int | None = None
    discrimination_index: float | None = None
    topic_tag: str | None = None
    cognitive_level: str | None = None


@dataclass(frozen=True)
class QuestionMetadataUpdatePayload:
    difficulty: str | None = None
    difficulty_level: int | None = None
    discrimination_index: float | None = None
    topic_tag: str | None = None
    cognitive_level: str | None = None


class QuestionService:
    def __init__(self, repo: QuestionRepository):
        self._repo = repo

    def create_question(self, payload: QuestionCreatePayload) -> Question:
        self._validate_options(payload.options)
        now = utc_now_iso()
        question_id = str(uuid.uuid4())
        topic_tag = payload.topic_tag if payload.topic_tag else payload.topic
        question = Question(
            id=question_id,
            text=payload.text,
            topic=payload.topic,
            difficulty=payload.difficulty,
            marks=payload.marks,
            created_at=now,
            difficulty_level=payload.difficulty_level,
            discrimination_index=payload.discrimination_index,
            topic_tag=topic_tag,
            cognitive_level=payload.cognitive_level,
        )
        options = [
            Option(
                id=str(uuid.uuid4()),
                question_id=question_id,
                option_text=option_text,
                is_correct=is_correct,
            )
            for option_text, is_correct in payload.options
        ]
        self._repo.create_question(question, options)
        return question

    def list_questions(self) -> list[dict]:
        rows = self._repo.list_questions()
        return [
            {
                "id": question.id,
                "text": question.text,
                "topic": question.topic,
                "difficulty": question.difficulty,
                "marks": question.marks,
                "created_at": question.created_at,
                "difficulty_level": question.difficulty_level,
                "discrimination_index": question.discrimination_index,
                "topic_tag": question.topic_tag,
                "cognitive_level": question.cognitive_level,
                "options": [
                    {
                        "id": option.id,
                        "question_id": option.question_id,
                        "option_text": option.option_text,
                        "is_correct": option.is_correct,
                    }
                    for option in options
                ],
            }
            for question, options in rows
        ]

    def delete_question(self, question_id: str) -> None:
        deleted = self._repo.delete_question(question_id)
        if not deleted:
            raise QuestionNotFoundError(f"Question '{question_id}' not found")

    def update_question_metadata(
        self,
        question_id: str,
        payload: QuestionMetadataUpdatePayload,
    ) -> Question:
        if not self._repo.question_exists(question_id):
            raise QuestionNotFoundError(f"Question '{question_id}' not found")

        changes = {
            "difficulty": payload.difficulty,
            "difficulty_level": payload.difficulty_level,
            "discrimination_index": payload.discrimination_index,
            "topic_tag": payload.topic_tag,
            "cognitive_level": payload.cognitive_level,
        }
        filtered_changes = {
            key: value
            for key, value in changes.items()
            if value is not None
        }
        if not filtered_changes:
            raise QuestionValidationError("At least one metadata field must be provided")

        updated = self._repo.update_question_metadata(question_id, filtered_changes)
        if not updated:
            raise QuestionValidationError("Question metadata update failed")

        question_row = self._repo.get_question_with_options(question_id)
        if question_row is None:
            raise QuestionNotFoundError(f"Question '{question_id}' not found")
        return question_row[0]

    def get_question_usage_statistics(self) -> list[dict]:
        return self._repo.list_usage_statistics()

    def _validate_options(self, options: list[tuple[str, bool]]) -> None:
        if len(options) < 2:
            raise QuestionValidationError("At least two options are required")
        correct_count = sum(1 for _, is_correct in options if is_correct)
        if correct_count != 1:
            raise QuestionValidationError("Exactly one correct option is required")
