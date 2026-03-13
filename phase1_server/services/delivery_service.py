"""Business logic for student exam delivery flow."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from phase1_server.models import Attempt, AttemptResponse, AttemptStatus, ExamStatus
from phase1_server.repositories.attempt_repository import AttemptRepository
from phase1_server.repositories.exam_repository import ExamRepository
from phase1_server.repositories.question_repository import QuestionRepository
from phase1_server.services.ai_analysis_service import AIAnalysisService
from phase1_server.services.attempt_state_service import (
    AttemptStateService,
    AttemptConcurrencyError,
    InvalidAttemptTransitionError,
)
from phase1_server.services.audit_service import AuditService
from phase1_server.services.exam_service import ExamNotFoundError, ExamService, ExamValidationError
from phase1_server.services.grading_service import GradingEngine, GradingError
from phase1_server.services.metrics_service import MetricsService


class DeliveryError(ValueError):
    pass


class OwnershipError(DeliveryError):
    pass


class AttemptStateError(DeliveryError):
    pass


class SnapshotQuestionNotFoundError(DeliveryError):
    pass


class AnalysisQuestionNotFoundError(DeliveryError):
    pass


class AuditEventType:
    ATTEMPT_STARTED = "ATTEMPT_STARTED"
    ANSWER_SUBMITTED = "ANSWER_SUBMITTED"
    FINALIZED = "FINALIZED"
    AUTO_EXPIRE = "AUTO_EXPIRE"
    GRADED = "GRADED"
    RESULT_VIEWED = "RESULT_VIEWED"
    CONCURRENCY_CONFLICT = "CONCURRENCY_CONFLICT"
    FORCE_FINALIZED = "FORCE_FINALIZED"
    ATTEMPT_PAUSED = "ATTEMPT_PAUSED"
    ATTEMPT_RESUMED = "ATTEMPT_RESUMED"
    EXAM_PAUSED = "EXAM_PAUSED"
    EXAM_RESUMED = "EXAM_RESUMED"
    EXAM_BROADCAST = "EXAM_BROADCAST"
    BROADCAST_RECEIVED = "BROADCAST_RECEIVED"
    QUESTION_ISSUE_REPORTED = "QUESTION_ISSUE_REPORTED"
    TECHNICAL_ISSUE_REPORTED = "TECHNICAL_ISSUE_REPORTED"
    RESULT_ANALYSIS_VIEWED = "RESULT_ANALYSIS_VIEWED"
    AI_EXPLANATION_GENERATED = "AI_EXPLANATION_GENERATED"


@dataclass(frozen=True)
class AnswerSubmissionPayload:
    attempt_id: str
    question_id: str
    selected_option_id: str
    confidence_tag: str | None = None


class DeliveryService:
    def __init__(
        self,
        attempt_repo: AttemptRepository,
        exam_repo: ExamRepository,
        question_repo: QuestionRepository,
        analytics_repo=None,
        now_provider: Callable[[], datetime] | None = None,
        audit_service: AuditService | None = None,
        metrics_service: MetricsService | None = None,
    ):
        self._attempt_repo = attempt_repo
        self._exam_repo = exam_repo
        self._question_repo = question_repo
        self._analytics_repo = analytics_repo
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self._audit_service = audit_service
        self._metrics_service = metrics_service

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
                "confidence_tag": payload.confidence_tag,
            },
            created_at=answered_at,
            version=attempt.version,
        )
        return {
            "attempt_id": attempt.id,
            "question_id": payload.question_id,
            "selected_option_id": payload.selected_option_id,
            "confidence_tag": payload.confidence_tag,
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
                self._record_metric_safely("increment_concurrency_conflict")
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

        self._record_metric_safely("increment_auto_expire")
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
                self._record_metric_safely("increment_concurrency_conflict")
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

    def auto_submit_expired_attempt_for_student(
        self,
        attempt_id: str,
        student_id: str,
    ) -> dict:
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise DeliveryError(f"Attempt '{attempt_id}' not found")
        if attempt.candidate_id != student_id:
            raise OwnershipError("Attempt does not belong to student")

        if attempt.status is AttemptStatus.FINALIZED:
            return self._grade_and_build_finalize_response(
                attempt_id=attempt.id,
                finalized_at=attempt.updated_at,
            )

        if not self._attempt_repo.is_expired(attempt.id, self._now_iso()):
            raise AttemptStateError("Attempt timer has not elapsed yet")

        result = self.force_finalize_expired_attempt(attempt.id)
        return {
            **result,
            "auto_submitted": True,
        }

    def force_finalize_attempt_by_admin(
        self,
        attempt_id: str,
        actor_id: str = "admin",
        reason: str | None = None,
    ) -> dict:
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise DeliveryError(f"Attempt '{attempt_id}' not found")

        state_service = AttemptStateService(self._attempt_repo)
        current = attempt
        finalized_at = current.updated_at

        if current.status is AttemptStatus.CREATED:
            try:
                state_service.transition(current.id, AttemptStatus.ACTIVE)
            except (AttemptConcurrencyError, InvalidAttemptTransitionError) as exc:
                raise AttemptStateError(str(exc)) from exc
            refreshed = self._attempt_repo.get(current.id)
            if refreshed is None:
                raise DeliveryError(f"Attempt '{attempt_id}' not found")
            current = refreshed

        if current.status in {AttemptStatus.ACTIVE, AttemptStatus.PAUSED}:
            try:
                transition = state_service.transition(current.id, AttemptStatus.FINALIZED)
            except AttemptConcurrencyError as exc:
                self._record_metric_safely("increment_concurrency_conflict")
                self._log_event_safely(
                    entity_type="attempt",
                    entity_id=current.id,
                    actor_type="admin",
                    actor_id=actor_id,
                    event_type=AuditEventType.CONCURRENCY_CONFLICT,
                    payload={"error": str(exc), "reason": reason},
                )
                raise AttemptStateError(str(exc)) from exc
            except InvalidAttemptTransitionError as exc:
                raise AttemptStateError(str(exc)) from exc

            finalized_at = transition.updated_at
            self._attempt_repo.log_audit_event(
                attempt_id=current.id,
                event_type=AuditEventType.FINALIZED,
                timestamp=finalized_at,
                actor_id=actor_id,
                actor_role="admin",
            )
        elif current.status is AttemptStatus.FINALIZED:
            finalized_at = current.updated_at
        else:
            raise AttemptStateError(
                f"Attempt in state '{current.status.value}' cannot be force submitted"
            )

        self._log_event_safely(
            entity_type="attempt",
            entity_id=current.id,
            actor_type="admin",
            actor_id=actor_id,
            event_type=AuditEventType.FORCE_FINALIZED,
            payload={"reason": reason},
            created_at=finalized_at,
        )

        response = self._grade_and_build_finalize_response(
            attempt_id=current.id,
            finalized_at=finalized_at,
        )
        return {
            **response,
            "forced": True,
            "forced_by": actor_id,
            "force_reason": reason,
        }

    def force_finalize_expired_attempts(
        self,
        actor_id: str = "admin",
        exam_id: str | None = None,
        limit: int = 500,
    ) -> dict:
        if limit < 1 or limit > 5000:
            raise DeliveryError("limit must be between 1 and 5000")
        if exam_id is not None and self._exam_repo.get_exam(exam_id) is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")

        now_iso = self._now_iso()
        attempt_ids = self._attempt_repo.list_expired_active_attempt_ids(
            now_iso=now_iso,
            exam_id=exam_id,
            limit=limit,
        )

        finalized_attempts: list[dict] = []
        failures: list[dict] = []
        for attempt_id in attempt_ids:
            self._record_metric_safely("increment_auto_expire")
            try:
                result = self.force_finalize_attempt_by_admin(
                    attempt_id=attempt_id,
                    actor_id=actor_id,
                    reason="expired_bulk_force_submit",
                )
                finalized_attempts.append(
                    {
                        "attempt_id": attempt_id,
                        "status": result["status"],
                        "finalized_at": result["finalized_at"],
                    }
                )
            except (AttemptStateError, DeliveryError) as exc:
                failures.append(
                    {
                        "attempt_id": attempt_id,
                        "error": str(exc),
                    }
                )

        return {
            "exam_id": exam_id,
            "processed_count": len(attempt_ids),
            "finalized_count": len(finalized_attempts),
            "failed_count": len(failures),
            "finalized_attempts": finalized_attempts,
            "failures": failures,
        }

    def pause_exam_attempts(
        self,
        exam_id: str,
        actor_id: str = "admin",
        reason: str | None = None,
        limit: int = 2000,
    ) -> dict:
        if limit < 1 or limit > 5000:
            raise DeliveryError("limit must be between 1 and 5000")
        if self._exam_repo.get_exam(exam_id) is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")

        attempt_ids = self._attempt_repo.list_attempt_ids_by_exam_and_status(
            exam_id=exam_id,
            status=AttemptStatus.ACTIVE,
            limit=limit,
        )
        state_service = AttemptStateService(self._attempt_repo)
        paused: list[dict] = []
        failures: list[dict] = []
        for attempt_id in attempt_ids:
            try:
                transition = state_service.transition(attempt_id, AttemptStatus.PAUSED)
                self._attempt_repo.log_audit_event(
                    attempt_id=attempt_id,
                    event_type="PAUSED",
                    timestamp=transition.updated_at,
                    actor_id=actor_id,
                    actor_role="admin",
                )
                self._log_event_safely(
                    entity_type="attempt",
                    entity_id=attempt_id,
                    actor_type="admin",
                    actor_id=actor_id,
                    event_type=AuditEventType.ATTEMPT_PAUSED,
                    payload={"reason": reason},
                    created_at=transition.updated_at,
                    version=transition.version,
                )
                paused.append({"attempt_id": attempt_id, "paused_at": transition.updated_at})
            except (AttemptConcurrencyError, InvalidAttemptTransitionError) as exc:
                failures.append({"attempt_id": attempt_id, "error": str(exc)})

        self._log_event_safely(
            entity_type="exam",
            entity_id=exam_id,
            actor_type="admin",
            actor_id=actor_id,
            event_type=AuditEventType.EXAM_PAUSED,
            payload={
                "reason": reason,
                "processed_count": len(attempt_ids),
                "paused_count": len(paused),
                "failed_count": len(failures),
            },
        )
        return {
            "exam_id": exam_id,
            "processed_count": len(attempt_ids),
            "paused_count": len(paused),
            "failed_count": len(failures),
            "paused_attempts": paused,
            "failures": failures,
        }

    def resume_exam_attempts(
        self,
        exam_id: str,
        actor_id: str = "admin",
        reason: str | None = None,
        limit: int = 2000,
    ) -> dict:
        if limit < 1 or limit > 5000:
            raise DeliveryError("limit must be between 1 and 5000")
        if self._exam_repo.get_exam(exam_id) is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")

        attempt_ids = self._attempt_repo.list_attempt_ids_by_exam_and_status(
            exam_id=exam_id,
            status=AttemptStatus.PAUSED,
            limit=limit,
        )
        state_service = AttemptStateService(self._attempt_repo)
        resumed: list[dict] = []
        failures: list[dict] = []
        for attempt_id in attempt_ids:
            try:
                transition = state_service.transition(attempt_id, AttemptStatus.ACTIVE)
                self._attempt_repo.log_audit_event(
                    attempt_id=attempt_id,
                    event_type="RESUMED",
                    timestamp=transition.updated_at,
                    actor_id=actor_id,
                    actor_role="admin",
                )
                self._log_event_safely(
                    entity_type="attempt",
                    entity_id=attempt_id,
                    actor_type="admin",
                    actor_id=actor_id,
                    event_type=AuditEventType.ATTEMPT_RESUMED,
                    payload={"reason": reason},
                    created_at=transition.updated_at,
                    version=transition.version,
                )
                resumed.append({"attempt_id": attempt_id, "resumed_at": transition.updated_at})
            except (AttemptConcurrencyError, InvalidAttemptTransitionError) as exc:
                failures.append({"attempt_id": attempt_id, "error": str(exc)})

        self._log_event_safely(
            entity_type="exam",
            entity_id=exam_id,
            actor_type="admin",
            actor_id=actor_id,
            event_type=AuditEventType.EXAM_RESUMED,
            payload={
                "reason": reason,
                "processed_count": len(attempt_ids),
                "resumed_count": len(resumed),
                "failed_count": len(failures),
            },
        )
        return {
            "exam_id": exam_id,
            "processed_count": len(attempt_ids),
            "resumed_count": len(resumed),
            "failed_count": len(failures),
            "resumed_attempts": resumed,
            "failures": failures,
        }

    def publish_exam_broadcast(
        self,
        exam_id: str,
        message: str,
        severity: str = "info",
        actor_id: str = "admin",
    ) -> dict:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")

        normalized_message = (message or "").strip()
        if len(normalized_message) < 3:
            raise DeliveryError("message must be at least 3 characters")
        normalized_severity = (severity or "info").strip().lower()
        if normalized_severity not in {"info", "warn", "critical"}:
            raise DeliveryError("severity must be one of: info, warn, critical")

        created_at = self._now_iso()
        payload = {
            "exam_id": exam_id,
            "message": normalized_message,
            "severity": normalized_severity,
        }
        if self._audit_service is None:
            raise DeliveryError("Audit service unavailable for broadcast persistence")
        try:
            self._audit_service.log_event(
                entity_type="exam",
                entity_id=exam_id,
                actor_type="admin",
                actor_id=actor_id,
                event_type=AuditEventType.EXAM_BROADCAST,
                payload=payload,
                created_at=created_at,
            )
        except Exception as exc:
            raise DeliveryError("Unable to persist broadcast event") from exc
        return {
            "exam_id": exam_id,
            "exam_name": exam.name,
            "message": normalized_message,
            "severity": normalized_severity,
            "broadcast_at": created_at,
        }

    def list_attempt_broadcasts(
        self,
        attempt_id: str,
        student_id: str,
        since: str | None = None,
        limit: int = 20,
    ) -> dict:
        if limit < 1 or limit > 200:
            raise DeliveryError("limit must be between 1 and 200")
        attempt = self._assert_owned_attempt(attempt_id, student_id)
        if self._audit_service is None:
            return {
                "attempt_id": attempt.id,
                "exam_id": attempt.exam_id,
                "count": 0,
                "broadcasts": [],
            }

        timeline = self._audit_service.list_entity_timeline("exam", attempt.exam_id)
        filtered = [
            event
            for event in timeline
            if event.get("event_type") == AuditEventType.EXAM_BROADCAST
            and (since is None or event.get("created_at", "") > since)
        ]
        selected = filtered[-limit:]
        broadcasts = [
            {
                "id": event.get("id"),
                "exam_id": attempt.exam_id,
                "actor_id": event.get("actor_id"),
                "created_at": event.get("created_at"),
                "message": (event.get("payload") or {}).get("message"),
                "severity": (event.get("payload") or {}).get("severity", "info"),
            }
            for event in selected
        ]
        return {
            "attempt_id": attempt.id,
            "exam_id": attempt.exam_id,
            "count": len(broadcasts),
            "broadcasts": broadcasts,
        }

    def acknowledge_attempt_broadcasts(
        self,
        attempt_id: str,
        student_id: str,
        broadcast_ids: list[str],
        received_at: str | None = None,
    ) -> dict:
        attempt = self._assert_owned_attempt(attempt_id, student_id)
        normalized_ids: list[str] = []
        seen: set[str] = set()
        for broadcast_id in broadcast_ids:
            value = str(broadcast_id or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized_ids.append(value)
            if len(normalized_ids) >= 50:
                break

        if self._audit_service is None or not normalized_ids:
            return {
                "attempt_id": attempt.id,
                "exam_id": attempt.exam_id,
                "acknowledged_count": 0,
                "already_acknowledged_count": 0,
                "ignored_count": len(normalized_ids),
                "acknowledged_broadcast_ids": [],
            }

        timeline = self._audit_service.list_entity_timeline("exam", attempt.exam_id)
        known_broadcast_ids = {
            event.get("id")
            for event in timeline
            if event.get("event_type") == AuditEventType.EXAM_BROADCAST
        }
        existing_receipts = {
            (
                (event.get("payload") or {}).get("broadcast_event_id"),
                event.get("actor_id"),
                (event.get("payload") or {}).get("attempt_id"),
            )
            for event in timeline
            if event.get("event_type") == AuditEventType.BROADCAST_RECEIVED
        }

        ack_at = received_at or self._now_iso()
        acknowledged_count = 0
        already_acknowledged_count = 0
        ignored_count = 0
        acknowledged_ids: list[str] = []
        for broadcast_id in normalized_ids:
            if broadcast_id not in known_broadcast_ids:
                ignored_count += 1
                continue

            receipt_key = (broadcast_id, student_id, attempt.id)
            if receipt_key in existing_receipts:
                already_acknowledged_count += 1
                continue

            payload = {
                "exam_id": attempt.exam_id,
                "attempt_id": attempt.id,
                "student_id": student_id,
                "broadcast_event_id": broadcast_id,
            }
            try:
                self._audit_service.log_event(
                    entity_type="exam",
                    entity_id=attempt.exam_id,
                    actor_type="student",
                    actor_id=student_id,
                    event_type=AuditEventType.BROADCAST_RECEIVED,
                    payload=payload,
                    created_at=ack_at,
                )
            except Exception:
                ignored_count += 1
                continue
            existing_receipts.add(receipt_key)
            acknowledged_ids.append(broadcast_id)
            acknowledged_count += 1

        return {
            "attempt_id": attempt.id,
            "exam_id": attempt.exam_id,
            "acknowledged_count": acknowledged_count,
            "already_acknowledged_count": already_acknowledged_count,
            "ignored_count": ignored_count,
            "acknowledged_broadcast_ids": acknowledged_ids,
        }

    def report_question_issue(
        self,
        attempt_id: str,
        question_id: str,
        issue_type: str,
        note: str | None,
        student_id: str,
    ) -> dict:
        attempt = self._assert_owned_active_attempt(attempt_id, student_id)
        if not self._attempt_repo.question_in_snapshot(attempt.id, question_id):
            raise SnapshotQuestionNotFoundError(
                "Question does not belong to attempt snapshot"
            )
        created_at = self._now_iso()
        payload = {
            "question_id": question_id,
            "issue_type": issue_type,
            "note": note,
        }
        self._log_event_safely(
            entity_type="attempt",
            entity_id=attempt.id,
            actor_type="student",
            actor_id=student_id,
            event_type=AuditEventType.QUESTION_ISSUE_REPORTED,
            payload=payload,
            created_at=created_at,
            version=attempt.version,
        )
        return {
            "attempt_id": attempt.id,
            "question_id": question_id,
            "issue_type": issue_type,
            "note": note,
            "reported_at": created_at,
            "reported": True,
        }

    def report_technical_issue(
        self,
        attempt_id: str,
        issue_type: str,
        note: str | None,
        student_id: str,
    ) -> dict:
        attempt = self._assert_owned_active_attempt(attempt_id, student_id)
        created_at = self._now_iso()
        payload = {
            "issue_type": issue_type,
            "note": note,
        }
        self._log_event_safely(
            entity_type="attempt",
            entity_id=attempt.id,
            actor_type="student",
            actor_id=student_id,
            event_type=AuditEventType.TECHNICAL_ISSUE_REPORTED,
            payload=payload,
            created_at=created_at,
            version=attempt.version,
        )
        return {
            "attempt_id": attempt.id,
            "issue_type": issue_type,
            "note": note,
            "reported_at": created_at,
            "reported": True,
        }

    def get_attempt_exam_rules(self, attempt_id: str, student_id: str) -> dict:
        attempt = self._assert_owned_attempt(attempt_id, student_id)
        exam = self._exam_repo.get_exam(attempt.exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{attempt.exam_id}' not found")

        rules = [
            "Read each question carefully before selecting an option.",
            "Use Save & Next to persist each answer.",
            "Do not switch tabs or open external resources during attempt.",
            "Keep LAN connected; local queue auto-syncs on reconnect.",
            "Review marked/unanswered items before final submission.",
        ]
        return {
            "attempt_id": attempt.id,
            "exam_id": exam.id,
            "exam_name": exam.name,
            "duration_minutes": exam.duration_minutes,
            "negative_marking": exam.negative_marking,
            "rules": rules,
        }

    def get_result(self, attempt_id: str, student_id: str) -> dict:
        result = self._load_result_payload(attempt_id, student_id)
        self._attempt_repo.log_audit_event(
            attempt_id=attempt_id,
            event_type=AuditEventType.RESULT_VIEWED,
            timestamp=self._now_iso(),
            actor_id=student_id,
            actor_role="student",
        )
        return result

    def get_attempt_analysis(self, attempt_id: str, student_id: str) -> dict:
        result = self._load_result_payload(attempt_id, student_id)
        question_results = [
            row
            for row in result.get("question_results", [])
            if str(row.get("status")) in {"incorrect", "skipped"}
        ]
        ai_service = AIAnalysisService()
        summary = ai_service.summarize_attempt(question_results)
        self._attempt_repo.log_audit_event(
            attempt_id=attempt_id,
            event_type=AuditEventType.RESULT_ANALYSIS_VIEWED,
            timestamp=self._now_iso(),
            actor_id=student_id,
            actor_role="student",
        )
        self._log_event_safely(
            entity_type="attempt",
            entity_id=attempt_id,
            actor_type="student",
            actor_id=student_id,
            event_type=AuditEventType.RESULT_ANALYSIS_VIEWED,
            payload={
                "question_count": len(question_results),
                "provider": summary.get("provider", "heuristic"),
            },
        )
        return {
            "attempt_id": attempt_id,
            "exam_id": result.get("exam_id"),
            "question_count": len(question_results),
            "incorrect_or_skipped_questions": question_results,
            "summary": summary.get("summary"),
            "weak_topics": summary.get("weak_topics", []),
            "learning_path": summary.get("learning_path", []),
            "provider": summary.get("provider", "heuristic"),
            "provider_status": summary.get("provider_status", {}),
        }

    def explain_attempt_question(
        self,
        attempt_id: str,
        question_id: str,
        student_id: str,
    ) -> dict:
        result = self._load_result_payload(attempt_id, student_id)
        target = next(
            (
                row
                for row in result.get("question_results", [])
                if str(row.get("question_id")) == str(question_id)
            ),
            None,
        )
        if target is None:
            raise AnalysisQuestionNotFoundError(
                f"Question '{question_id}' not found in attempt result"
            )
        if str(target.get("status")) == "correct":
            raise DeliveryError("AI explanation is available only for incorrect or skipped questions")

        ai_service = AIAnalysisService()
        explanation = ai_service.explain_question(
            question_text=str(target.get("question_text") or "Question unavailable"),
            user_answer=target.get("selected_option_text"),
            correct_answer=target.get("correct_option_text"),
            topic=target.get("topic"),
            difficulty=target.get("difficulty"),
            status=str(target.get("status") or "incorrect"),
        )
        created_at = self._now_iso()
        self._attempt_repo.log_audit_event(
            attempt_id=attempt_id,
            event_type=AuditEventType.AI_EXPLANATION_GENERATED,
            timestamp=created_at,
            actor_id=student_id,
            actor_role="student",
        )
        self._log_event_safely(
            entity_type="attempt",
            entity_id=attempt_id,
            actor_type="student",
            actor_id=student_id,
            event_type=AuditEventType.AI_EXPLANATION_GENERATED,
            created_at=created_at,
            payload={
                "question_id": question_id,
                "provider": explanation.get("provider", "heuristic"),
                "status": target.get("status"),
            },
        )
        return {
            "attempt_id": attempt_id,
            "question_id": question_id,
            "status": target.get("status"),
            "topic": target.get("topic"),
            "question_text": target.get("question_text"),
            "selected_option_text": target.get("selected_option_text"),
            "correct_option_text": target.get("correct_option_text"),
            "provider": explanation.get("provider", "heuristic"),
            "provider_status": explanation.get("provider_status", {}),
            "analysis": explanation,
        }

    def _load_result_payload(self, attempt_id: str, student_id: str) -> dict:
        engine = GradingEngine(
            self._attempt_repo, self._exam_repo, self._question_repo, self._analytics_repo
        )
        return engine.get_result(attempt_id, student_id)

    def get_attempt_status(self, attempt_id: str, student_id: str) -> dict:
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise DeliveryError(f"Attempt '{attempt_id}' not found")
        if attempt.candidate_id != student_id:
            raise OwnershipError("Attempt does not belong to student")

        snapshot_question_ids = self._attempt_repo.list_snapshot_question_ids(attempt.id)
        responses = self._attempt_repo.get_responses(attempt.id)

        sequence_by_question_id = {
            question_id: sequence
            for sequence, question_id in enumerate(snapshot_question_ids, start=1)
        }
        answered = [
            {
                "sequence_number": sequence_by_question_id[question_id],
                "question_id": question_id,
                "selected_option_id": selected_option_id,
            }
            for question_id, selected_option_id in responses.items()
            if question_id in sequence_by_question_id
        ]
        answered.sort(key=lambda item: item["sequence_number"])

        return {
            "attempt_id": attempt.id,
            "exam_id": attempt.exam_id,
            "status": attempt.status.value,
            "started_at": attempt.created_at,
            "expires_at": attempt.expires_at,
            "total_question_count": len(snapshot_question_ids),
            "answered_question_count": len(answered),
            "answered": answered,
        }

    def _grade_and_build_finalize_response(self, attempt_id: str, finalized_at: str) -> dict:
        grading_engine = GradingEngine(
            self._attempt_repo,
            self._exam_repo,
            self._question_repo,
            self._analytics_repo,
        )
        start = time.perf_counter()
        try:
            summary = grading_engine.grade_attempt(attempt_id, graded_at=finalized_at)
        except GradingError as exc:
            self._record_metric_safely("record_finalize_to_grade_duration", (time.perf_counter() - start) * 1000.0)
            raise DeliveryError(str(exc)) from exc

        self._record_metric_safely("record_finalize_to_grade_duration", (time.perf_counter() - start) * 1000.0)

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

    def _assert_owned_attempt(self, attempt_id: str, student_id: str) -> Attempt:
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise DeliveryError(f"Attempt '{attempt_id}' not found")
        if attempt.candidate_id != student_id:
            raise OwnershipError("Attempt does not belong to student")
        return attempt

    def _assert_owned_active_attempt(self, attempt_id: str, student_id: str) -> Attempt:
        attempt = self._assert_owned_attempt(attempt_id, student_id)
        if attempt.status != AttemptStatus.ACTIVE:
            raise AttemptStateError(
                f"Attempt state must be active, got {attempt.status.value}"
            )

        if self._attempt_repo.is_expired(attempt.id, self._now_iso()):
            self._record_metric_safely("increment_auto_expire")
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

    def _record_metric_safely(self, method_name: str, *args) -> None:
        if self._metrics_service is None:
            return
        method = getattr(self._metrics_service, method_name, None)
        if method is None:
            return
        try:
            method(*args)
        except Exception:
            return

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
