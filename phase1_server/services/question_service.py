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


class QuestionService:
    def __init__(self, repo: QuestionRepository):
        self._repo = repo

    def create_question(self, payload: QuestionCreatePayload) -> Question:
        self._validate_options(payload.options)
        now = utc_now_iso()
        question_id = str(uuid.uuid4())
        question = Question(
            id=question_id,
            text=payload.text,
            topic=payload.topic,
            difficulty=payload.difficulty,
            marks=payload.marks,
            created_at=now,
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

    def _validate_options(self, options: list[tuple[str, bool]]) -> None:
        if len(options) < 2:
            raise QuestionValidationError("At least two options are required")
        correct_count = sum(1 for _, is_correct in options if is_correct)
        if correct_count != 1:
            raise QuestionValidationError("Exactly one correct option is required")
