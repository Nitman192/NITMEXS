"""Business logic for student exam delivery flow."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from phase1_server.models import Attempt, AttemptResponse, AttemptStatus, ExamStatus
from phase1_server.repositories.attempt_repository import AttemptRepository
from phase1_server.repositories.exam_repository import ExamRepository
from phase1_server.repositories.question_repository import QuestionRepository
from phase1_server.services.attempt_state_service import (
    AttemptStateService,
    AttemptConcurrencyError,
    InvalidAttemptTransitionError,
)
from phase1_server.services.audit_service import AuditService
from phase1_server.services.exam_service import ExamNotFoundError, ExamService, ExamValidationError
from phase1_server.services.grading_service import GradingEngine, GradingError


class DeliveryError(ValueError):
    pass


class OwnershipError(DeliveryError):
    pass


class AttemptStateError(DeliveryError):
    pass


class SnapshotQuestionNotFoundError(DeliveryError):
    pass


class AuditEventType:
    ATTEMPT_STARTED = "ATTEMPT_STARTED"
    ANSWER_SUBMITTED = "ANSWER_SUBMITTED"
    FINALIZED = "FINALIZED"
    AUTO_EXPIRE = "AUTO_EXPIRE"
    GRADED = "GRADED"
    RESULT_VIEWED = "RESULT_VIEWED"
    CONCURRENCY_CONFLICT = "CONCURRENCY_CONFLICT"


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
        audit_service: AuditService | None = None,
    ):
        self._attempt_repo = attempt_repo
        self._exam_repo = exam_repo
        self._question_repo = question_repo
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._audit_service = audit_service

    def start_attempt(self, exam_id: str, student_id: str) -> dict:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")
        if exam.status is not ExamStatus.ACTIVE:
            raise ExamValidationError("Exam is not active")

        existing = self._attempt_repo.get_by_candidate_and_exam(student_id, exam_id)
        if existing and existing.status in {AttemptStatus.ACTIVE, AttemptStatus.FINALIZED}:
            raise AttemptStateError("Attempt already started for this exam")

        now = self._now_iso()
        expires_at = self._calculate_expires_at(now, exam.duration_minutes)
        attempt = Attempt(
            id=str(uuid.uuid4()),
            candidate_id=student_id,
            exam_id=exam_id,
            status=AttemptStatus.CREATED,
            created_at=now,
            updated_at=now,
            submitted_at=None,
            expires_at=expires_at,
        )
        self._attempt_repo.create(attempt)

        state_service = AttemptStateService(self._attempt_repo)
        state_service.transition(attempt.id, AttemptStatus.ACTIVE)

        exam_service = ExamService(self._exam_repo, self._question_repo, self._audit_service)
        snapshot = exam_service.generate_exam_snapshot(exam_id=exam_id, attempt_id=attempt.id)
        first = next((item for item in snapshot if item["order_index"] == 1), None)
        if first is None:
            raise DeliveryError("Unable to generate first question")
        question_payload = self._question_public_payload(first["question_id"])
        self._log_event_safely(
            entity_type="attempt",
            entity_id=attempt.id,
            actor_type="student",
            actor_id=student_id,
            event_type=AuditEventType.ATTEMPT_STARTED,
            payload={"exam_id": exam_id, "expires_at": expires_at},
            version=attempt.version,
        )

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
        self._log_event_safely(
            entity_type="attempt",
            entity_id=attempt.id,
            actor_type="student",
            actor_id=student_id,
            event_type=AuditEventType.ANSWER_SUBMITTED,
            payload={
                "question_id": payload.question_id,
                "selected_option_id": payload.selected_option_id,
            },
            created_at=answered_at,
            version=attempt.version,
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

        if attempt.status != AttemptStatus.FINALIZED and self._attempt_repo.is_expired(
            attempt.id,
            self._now_iso(),
        ):
            raise AttemptStateError("Attempt expired; use force finalize")

        finalized_at = attempt.updated_at
        if attempt.status != AttemptStatus.FINALIZED:
            state_service = AttemptStateService(self._attempt_repo)
            try:
                result = state_service.transition(attempt.id, AttemptStatus.FINALIZED)
            except AttemptConcurrencyError as exc:
                self._log_event_safely(
                    entity_type="attempt",
                    entity_id=attempt.id,
                    actor_type="student",
                    actor_id=student_id,
                    event_type=AuditEventType.CONCURRENCY_CONFLICT,
                    payload={"error": str(exc)},
                )
                raise AttemptStateError(str(exc)) from exc
            except InvalidAttemptTransitionError as exc:
                raise AttemptStateError(str(exc)) from exc
            finalized_at = result.updated_at
            self._attempt_repo.log_audit_event(
                attempt_id=attempt.id,
                event_type=AuditEventType.FINALIZED,
                timestamp=finalized_at,
                actor_id=student_id,
                actor_role="student",
            )
            self._log_event_safely(
                entity_type="attempt",
                entity_id=attempt.id,
                actor_type="student",
                actor_id=student_id,
                event_type=AuditEventType.FINALIZED,
                created_at=finalized_at,
                version=result.version,
            )

        return self._grade_and_build_finalize_response(
            attempt_id=attempt.id,
            finalized_at=finalized_at,
        )

    def force_finalize_expired_attempt(self, attempt_id: str) -> dict:
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise DeliveryError(f"Attempt '{attempt_id}' not found")

        if not self._attempt_repo.is_expired(attempt_id, self._now_iso()):
            raise AttemptStateError("Attempt is not expired")

        self._log_event_safely(
            entity_type="attempt",
            entity_id=attempt.id,
            actor_type="system",
            actor_id="system",
            event_type=AuditEventType.AUTO_EXPIRE,
            payload={"reason": "expired_attempt_force_finalize"},
        )

        finalized_at = attempt.updated_at
        if attempt.status != AttemptStatus.FINALIZED:
            state_service = AttemptStateService(self._attempt_repo)
            try:
                result = state_service.transition(attempt.id, AttemptStatus.FINALIZED)
            except AttemptConcurrencyError as exc:
                self._log_event_safely(
                    entity_type="attempt",
                    entity_id=attempt.id,
                    actor_type="system",
                    actor_id="system",
                    event_type=AuditEventType.CONCURRENCY_CONFLICT,
                    payload={"error": str(exc)},
                )
                raise AttemptStateError(str(exc)) from exc
            except InvalidAttemptTransitionError as exc:
                raise AttemptStateError(str(exc)) from exc
            finalized_at = result.updated_at
            self._attempt_repo.log_audit_event(
                attempt_id=attempt.id,
                event_type=AuditEventType.FINALIZED,
                timestamp=finalized_at,
                actor_id="system",
                actor_role="system",
            )
            self._log_event_safely(
                entity_type="attempt",
                entity_id=attempt.id,
                actor_type="system",
                actor_id="system",
                event_type=AuditEventType.FINALIZED,
                created_at=finalized_at,
                version=result.version,
            )

        return self._grade_and_build_finalize_response(
            attempt_id=attempt.id,
            finalized_at=finalized_at,
        )

    def get_result(self, attempt_id: str, student_id: str) -> dict:
        engine = GradingEngine(self._attempt_repo, self._exam_repo, self._question_repo)
        result = engine.get_result(attempt_id, student_id)
        self._attempt_repo.log_audit_event(
            attempt_id=attempt_id,
            event_type=AuditEventType.RESULT_VIEWED,
            timestamp=self._now_iso(),
            actor_id=student_id,
            actor_role="student",
        )
        return result

    def _grade_and_build_finalize_response(self, attempt_id: str, finalized_at: str) -> dict:
        grading_engine = GradingEngine(
            self._attempt_repo,
            self._exam_repo,
            self._question_repo,
        )
        try:
            summary = grading_engine.grade_attempt(attempt_id, graded_at=finalized_at)
        except GradingError as exc:
            raise DeliveryError(str(exc)) from exc

        if summary.graded_now:
            self._attempt_repo.log_audit_event(
                attempt_id=attempt_id,
                event_type=AuditEventType.GRADED,
                timestamp=finalized_at,
                actor_id="system",
                actor_role="system",
            )
            self._log_event_safely(
                entity_type="attempt",
                entity_id=attempt_id,
                actor_type="system",
                actor_id="system",
                event_type=AuditEventType.GRADED,
                created_at=finalized_at,
            )

        return {
            "attempt_id": attempt_id,
            "status": AttemptStatus.FINALIZED.value,
            "finalized_at": finalized_at,
            "grading": "completed",
            "result": {
                "total_score": summary.total_score,
                "total_possible_marks": summary.total_possible_marks,
                "percentage": summary.percentage,
                "passed": summary.passed,
            },
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

        if self._attempt_repo.is_expired(attempt.id, self._now_iso()):
            self._log_event_safely(
                entity_type="attempt",
                entity_id=attempt.id,
                actor_type="system",
                actor_id="system",
                event_type=AuditEventType.AUTO_EXPIRE,
                payload={"reason": "expired_during_access"},
            )
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

    def _log_event_safely(self, **kwargs) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.log_event(**kwargs)
        except Exception:
            return

    def _calculate_expires_at(self, started_at_iso: str, duration_minutes: int) -> str:
        started = datetime.fromisoformat(started_at_iso)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        return (started + timedelta(minutes=duration_minutes)).isoformat()

    def _now_iso(self) -> str:
        return self._now_provider().isoformat()
