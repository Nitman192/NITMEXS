"""Business logic for student exam delivery flow."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from phase1_server.models import Attempt, AttemptResponse, AttemptStatus
from phase1_server.repositories.attempt_repository import AttemptRepository
from phase1_server.repositories.exam_repository import ExamRepository
from phase1_server.repositories.question_repository import QuestionRepository
from phase1_server.services.attempt_state_service import (
    AttemptStateService,
    InvalidAttemptTransitionError,
)
from phase1_server.services.exam_service import ExamNotFoundError, ExamService, ExamValidationError


class DeliveryError(ValueError):
    pass


class OwnershipError(DeliveryError):
    pass


class AttemptStateError(DeliveryError):
    pass


class SnapshotQuestionNotFoundError(DeliveryError):
    pass


@dataclass(frozen=True)
class AnswerSubmissionPayload:
    attempt_id: str
    question_id: str
    selected_option_id: str


class DeliveryService:
    def __init__(
        self,
        attempt_repo: AttemptRepository,
        exam_repo: ExamRepository,
        question_repo: QuestionRepository,
        now_provider: Callable[[], datetime] | None = None,
    ):
        self._attempt_repo = attempt_repo
        self._exam_repo = exam_repo
        self._question_repo = question_repo
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def start_attempt(self, exam_id: str, student_id: str) -> dict:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")
        if not exam.published:
            raise ExamValidationError("Exam is not published")

        existing = self._attempt_repo.get_by_candidate_and_exam(student_id, exam_id)
        if existing and existing.status in {AttemptStatus.ACTIVE, AttemptStatus.FINALIZED}:
            raise AttemptStateError("Attempt already started for this exam")

        now = self._now_iso()
        attempt = Attempt(
            id=str(uuid.uuid4()),
            candidate_id=student_id,
            exam_id=exam_id,
            status=AttemptStatus.CREATED,
            created_at=now,
            updated_at=now,
            submitted_at=None,
        )
        self._attempt_repo.create(attempt)

        state_service = AttemptStateService(self._attempt_repo)
        state_service.transition(attempt.id, AttemptStatus.ACTIVE)

        exam_service = ExamService(self._exam_repo, self._question_repo)
        snapshot = exam_service.generate_exam_snapshot(exam_id=exam_id, attempt_id=attempt.id)
        first = next((item for item in snapshot if item["order_index"] == 1), None)
        if first is None:
            raise DeliveryError("Unable to generate first question")
        question_payload = self._question_public_payload(first["question_id"])

        expires_at = self._attempt_expires_at_iso(attempt, exam.duration_minutes)
        return {
            "attempt_id": attempt.id,
            "exam_id": exam_id,
            "started_at": attempt.created_at,
            "expires_at": expires_at,
            "status": AttemptStatus.ACTIVE.value,
            "first_question": {
                "sequence_number": 1,
                **question_payload,
            },
        }

    def fetch_question(
        self,
        attempt_id: str,
        sequence_number: int,
        student_id: str,
    ) -> dict:
        attempt = self._assert_owned_active_attempt(attempt_id, student_id)
        question_id = self._attempt_repo.get_snapshot_question_id(attempt.id, sequence_number)
        if question_id is None:
            raise SnapshotQuestionNotFoundError(
                f"No question found at sequence {sequence_number}"
            )

        return {
            "attempt_id": attempt_id,
            "sequence_number": sequence_number,
            **self._question_public_payload(question_id),
        }

    def submit_answer(self, payload: AnswerSubmissionPayload, student_id: str) -> dict:
        attempt = self._assert_owned_active_attempt(payload.attempt_id, student_id)
        if not self._attempt_repo.question_in_snapshot(attempt.id, payload.question_id):
            raise SnapshotQuestionNotFoundError(
                "Question does not belong to attempt snapshot"
            )
        if not self._question_repo.option_belongs_to_question(
            payload.question_id,
            payload.selected_option_id,
        ):
            raise DeliveryError("Selected option does not belong to question")

        answered_at = self._now_iso()
        self._attempt_repo.upsert_response(
            AttemptResponse(
                attempt_id=attempt.id,
                question_id=payload.question_id,
                selected_option_id=payload.selected_option_id,
                answered_at=answered_at,
            )
        )
        return {
            "attempt_id": attempt.id,
            "question_id": payload.question_id,
            "selected_option_id": payload.selected_option_id,
            "answered_at": answered_at,
            "idempotent": True,
        }

    def finalize_attempt(self, attempt_id: str, student_id: str) -> dict:
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise DeliveryError(f"Attempt '{attempt_id}' not found")
        if attempt.candidate_id != student_id:
            raise OwnershipError("Attempt does not belong to student")

        state_service = AttemptStateService(self._attempt_repo)
        try:
            result = state_service.transition(attempt.id, AttemptStatus.FINALIZED)
        except InvalidAttemptTransitionError as exc:
            raise AttemptStateError(str(exc)) from exc

        return {
            "attempt_id": result.attempt_id,
            "status": result.to_status.value,
            "finalized_at": result.updated_at,
            "grading": "queued",
        }

    def _assert_owned_active_attempt(self, attempt_id: str, student_id: str) -> Attempt:
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise DeliveryError(f"Attempt '{attempt_id}' not found")
        if attempt.candidate_id != student_id:
            raise OwnershipError("Attempt does not belong to student")
        if attempt.status != AttemptStatus.ACTIVE:
            raise AttemptStateError(
                f"Attempt state must be active, got {attempt.status.value}"
            )

        exam = self._exam_repo.get_exam(attempt.exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{attempt.exam_id}' not found")
        if self._is_expired(attempt.created_at, exam.duration_minutes):
            self._expire_attempt(attempt.id)
            raise AttemptStateError("Attempt has expired")
        return attempt

    def _question_public_payload(self, question_id: str) -> dict:
        row = self._question_repo.get_question_with_options(question_id)
        if row is None:
            raise SnapshotQuestionNotFoundError(f"Question '{question_id}' not found")

        question, options = row
        return {
            "question": {
                "id": question.id,
                "text": question.text,
                "topic": question.topic,
                "difficulty": question.difficulty,
                "marks": question.marks,
            },
            "options": [
                {
                    "id": option.id,
                    "option_text": option.option_text,
                }
                for option in options
            ],
        }

    def _expire_attempt(self, attempt_id: str) -> None:
        state_service = AttemptStateService(self._attempt_repo)
        try:
            state_service.transition(attempt_id, AttemptStatus.FINALIZED)
        except InvalidAttemptTransitionError:
            pass

    def _is_expired(self, started_at: str, duration_minutes: int) -> bool:
        started = datetime.fromisoformat(started_at)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        deadline = started + timedelta(minutes=duration_minutes)
        return self._now_provider() >= deadline

    def _attempt_expires_at_iso(self, attempt: Attempt, duration_minutes: int) -> str:
        started = datetime.fromisoformat(attempt.created_at)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        return (started + timedelta(minutes=duration_minutes)).isoformat()

    def _now_iso(self) -> str:
        return self._now_provider().isoformat()
