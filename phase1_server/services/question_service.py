"""Business logic for multi-type question management."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from phase1_server.models import Option, Question, QuestionType, QuestionVariantDecision, utc_now_iso
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
    owner_admin_id: str = "superadmin"
    created_by: str = "admin"
    question_type: str = QuestionType.MCQ_SINGLE.value
    options: list[tuple[str, bool]] | None = None
    accepted_answers: list[str] | None = None
    difficulty_level: int | None = None
    discrimination_index: float | None = None
    topic_tag: str | None = None
    cognitive_level: str | None = None
    word_target_min: int | None = None
    word_target_max: int | None = None
    word_hard_max: int | None = None


@dataclass(frozen=True)
class QuestionMetadataUpdatePayload:
    difficulty: str | None = None
    difficulty_level: int | None = None
    discrimination_index: float | None = None
    topic_tag: str | None = None
    cognitive_level: str | None = None
    word_target_min: int | None = None
    word_target_max: int | None = None
    word_hard_max: int | None = None


class QuestionService:
    def __init__(self, repo: QuestionRepository):
        self._repo = repo

    def create_question(self, payload: QuestionCreatePayload) -> Question:
        question_type = self._parse_question_type(payload.question_type)
        options = payload.options or []
        accepted_answers = payload.accepted_answers or []

        if question_type is QuestionType.MCQ_SINGLE:
            self._validate_options(options)
            if accepted_answers:
                raise QuestionValidationError("MCQ questions do not accept text answer variants")
            self._validate_word_policy(question_type, payload)
        elif question_type is QuestionType.TRUE_FALSE:
            options = self._build_true_false_options(options)
            if accepted_answers:
                raise QuestionValidationError("True/False questions do not accept text answer variants")
            self._validate_word_policy(question_type, payload)
        elif question_type is QuestionType.FIB_TEXT:
            if options:
                raise QuestionValidationError("Fill in the blanks questions cannot contain options")
            self._validate_word_policy(question_type, payload)
        else:
            if options:
                raise QuestionValidationError("Subjective questions cannot contain options")
            self._validate_subjective_word_policy(payload)

        now = utc_now_iso()
        question_id = str(uuid.uuid4())
        topic_tag = payload.topic_tag if payload.topic_tag else payload.topic
        created_by = (payload.created_by or "admin").strip() or "admin"
        question = Question(
            id=question_id,
            text=payload.text,
            topic=payload.topic,
            difficulty=payload.difficulty,
            marks=payload.marks,
            created_at=now,
            owner_admin_id=(payload.owner_admin_id or "superadmin").strip() or "superadmin",
            question_type=question_type,
            difficulty_level=payload.difficulty_level,
            discrimination_index=payload.discrimination_index,
            topic_tag=topic_tag,
            cognitive_level=payload.cognitive_level,
            word_target_min=payload.word_target_min,
            word_target_max=payload.word_target_max,
            word_hard_max=payload.word_hard_max,
        )
        option_models = [
            Option(
                id=str(uuid.uuid4()),
                question_id=question_id,
                option_text=option_text,
                is_correct=is_correct,
            )
            for option_text, is_correct in options
        ]
        variant_rows = [
            (
                str(uuid.uuid4()),
                answer_text,
                self.normalize_text_answer(answer_text),
                QuestionVariantDecision.ACCEPTED.value,
                created_by,
                now,
            )
            for answer_text in accepted_answers
            if answer_text.strip()
        ]
        self._repo.create_question(question, option_models, variant_rows)
        return question

    def list_questions(
        self,
        owner_admin_id: str | None = None,
        include_all: bool = False,
    ) -> list[dict]:
        rows = self._repo.list_questions(owner_admin_id=owner_admin_id, include_all=include_all)
        return [
            {
                "id": question.id,
                "text": question.text,
                "topic": question.topic,
                "difficulty": question.difficulty,
                "marks": question.marks,
                "created_at": question.created_at,
                "owner_admin_id": question.owner_admin_id,
                "question_type": question.question_type.value,
                "difficulty_level": question.difficulty_level,
                "discrimination_index": question.discrimination_index,
                "topic_tag": question.topic_tag,
                "cognitive_level": question.cognitive_level,
                "word_target_min": question.word_target_min,
                "word_target_max": question.word_target_max,
                "word_hard_max": question.word_hard_max,
                "options": [
                    {
                        "id": option.id,
                        "question_id": option.question_id,
                        "option_text": option.option_text,
                        "is_correct": option.is_correct,
                    }
                    for option in options
                ],
                "accepted_answers": [
                    {
                        "id": variant.id,
                        "answer_text": variant.answer_text,
                        "normalized_answer_text": variant.normalized_answer_text,
                        "decision": variant.decision.value,
                    }
                    for variant in variants
                ],
            }
            for question, options, variants in rows
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
        question = self._repo.get_question(question_id)
        if question is None:
            raise QuestionNotFoundError(f"Question '{question_id}' not found")

        if question.question_type in {QuestionType.SHORT_ANSWER, QuestionType.LONG_ANSWER}:
            self._validate_subjective_word_policy(
                QuestionMetadataUpdatePayload(
                    word_target_min=payload.word_target_min or question.word_target_min,
                    word_target_max=payload.word_target_max or question.word_target_max,
                    word_hard_max=payload.word_hard_max or question.word_hard_max,
                )
            )

        changes = {
            "difficulty": payload.difficulty,
            "difficulty_level": payload.difficulty_level,
            "discrimination_index": payload.discrimination_index,
            "topic_tag": payload.topic_tag,
            "cognitive_level": payload.cognitive_level,
            "word_target_min": payload.word_target_min,
            "word_target_max": payload.word_target_max,
            "word_hard_max": payload.word_hard_max,
        }
        filtered_changes = {key: value for key, value in changes.items() if value is not None}
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

    @staticmethod
    def normalize_text_answer(answer_text: str) -> str:
        lowered = answer_text.strip().lower()
        without_punctuation = re.sub(r"[^\w\s]", " ", lowered)
        return re.sub(r"\s+", " ", without_punctuation).strip()

    @staticmethod
    def count_words(answer_text: str) -> int:
        normalized = re.sub(r"\s+", " ", answer_text.strip())
        return 0 if not normalized else len(normalized.split(" "))

    def _validate_options(self, options: list[tuple[str, bool]]) -> None:
        if len(options) < 2:
            raise QuestionValidationError("At least two options are required")
        correct_count = sum(1 for _, is_correct in options if is_correct)
        if correct_count != 1:
            raise QuestionValidationError("Exactly one correct option is required")

    def _validate_word_policy(
        self,
        question_type: QuestionType,
        payload: QuestionCreatePayload,
    ) -> None:
        if question_type in {QuestionType.MCQ_SINGLE, QuestionType.TRUE_FALSE, QuestionType.FIB_TEXT}:
            if any(
                value is not None
                for value in [payload.word_target_min, payload.word_target_max, payload.word_hard_max]
            ):
                raise QuestionValidationError("Word limits are allowed only for short/long answers")

    def _validate_subjective_word_policy(
        self,
        payload: QuestionCreatePayload | QuestionMetadataUpdatePayload,
    ) -> None:
        minimum = payload.word_target_min
        maximum = payload.word_target_max
        hard_max = payload.word_hard_max
        if minimum is None or maximum is None or hard_max is None:
            raise QuestionValidationError(
                "Short/long answer questions require word_target_min, word_target_max, and word_hard_max"
            )
        if minimum <= 0 or maximum <= 0 or hard_max <= 0:
            raise QuestionValidationError("Word limits must be positive integers")
        if minimum > maximum:
            raise QuestionValidationError("word_target_min cannot exceed word_target_max")
        if maximum > hard_max:
            raise QuestionValidationError("word_target_max cannot exceed word_hard_max")

    @staticmethod
    def _parse_question_type(value: str) -> QuestionType:
        try:
            return QuestionType(value)
        except ValueError as exc:
            raise QuestionValidationError(f"Unsupported question_type '{value}'") from exc

    def _build_true_false_options(self, options: list[tuple[str, bool]]) -> list[tuple[str, bool]]:
        if not options:
            raise QuestionValidationError(
                "True/False questions require a correct value. Provide options with one correct choice."
            )
        correct_count = sum(1 for _, is_correct in options if is_correct)
        if correct_count != 1:
            raise QuestionValidationError("True/False questions require exactly one correct choice")
        correct_label = next((text for text, is_correct in options if is_correct), "").strip().lower()
        if correct_label not in {"true", "false", "t", "f"}:
            raise QuestionValidationError("True/False correct choice must be True or False")
        true_is_correct = correct_label in {"true", "t"}
        return [("True", true_is_correct), ("False", not true_is_correct)]
