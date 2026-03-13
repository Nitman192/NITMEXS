"""Business logic for exam management and randomized snapshot generation."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from typing import Any

from phase1_server.models import AttemptQuestionSnapshot, Exam, ExamStatus, utc_now_iso
from phase1_server.repositories.exam_repository import ExamRepository
from phase1_server.repositories.question_repository import QuestionRepository
from phase1_server.services.audit_service import AuditService


class ExamNotFoundError(ValueError):
    pass


class ExamAlreadyPublishedError(ValueError):
    pass


class ExamValidationError(ValueError):
    pass


class ExamDeleteBlockedError(ValueError):
    pass


class ExamEventType:
    EXAM_CLOSED = "EXAM_CLOSED"
    EXAM_PUBLISHED = "EXAM_PUBLISHED"
    EXAM_DELETED = "EXAM_DELETED"


@dataclass(frozen=True)
class ExamCreatePayload:
    name: str
    duration_minutes: int
    negative_marking: float


class ExamService:
    def __init__(
        self,
        exam_repo: ExamRepository,
        question_repo: QuestionRepository,
        audit_service: AuditService | None = None,
    ):
        self._exam_repo = exam_repo
        self._question_repo = question_repo
        self._audit_service = audit_service

    def create_exam(self, payload: ExamCreatePayload) -> Exam:
        if payload.duration_minutes <= 0:
            raise ExamValidationError("duration_minutes must be > 0")
        if payload.negative_marking < 0:
            raise ExamValidationError("negative_marking must be >= 0")

        exam = Exam(
            id=str(uuid.uuid4()),
            name=payload.name,
            duration_minutes=payload.duration_minutes,
            negative_marking=payload.negative_marking,
            status=ExamStatus.DRAFT,
            published=False,
            created_at=utc_now_iso(),
        )
        self._exam_repo.create_exam(exam)
        return exam

    def list_exams(self) -> list[Exam]:
        return self._exam_repo.list_exams()

    def delete_exam(self, exam_id: str, actor_id: str, actor_role: str = "admin") -> dict:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")
        if exam.status is ExamStatus.ACTIVE:
            raise ExamDeleteBlockedError("Active exams cannot be deleted. Close the exam first.")

        attempt_count = self._exam_repo.count_attempts(exam_id)
        if attempt_count > 0:
            raise ExamDeleteBlockedError(
                "Exam has attempt history and cannot be deleted safely."
            )

        self._log_event_safely(
            entity_type="exam",
            entity_id=exam_id,
            actor_type=actor_role,
            actor_id=actor_id,
            event_type=ExamEventType.EXAM_DELETED,
            payload={
                "name": exam.name,
                "status": exam.status.value,
                "attempt_count": attempt_count,
            },
        )
        self._exam_repo.delete_exam(exam_id)
        return {
            "exam_id": exam_id,
            "name": exam.name,
            "deleted": True,
            "attempt_count": attempt_count,
        }

    def add_questions(self, exam_id: str, question_ids: list[str]) -> None:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")
        if exam.status is not ExamStatus.DRAFT:
            raise ExamValidationError("Can only add questions to draft exams")

        for question_id in question_ids:
            if not self._question_repo.question_exists(question_id):
                raise ExamValidationError(f"Unknown question '{question_id}'")

        self._exam_repo.add_questions(exam_id, question_ids)

    def publish_exam(self, exam_id: str) -> Exam:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")
        if exam.status is ExamStatus.ACTIVE:
            raise ExamAlreadyPublishedError(f"Exam '{exam_id}' already published")
        if exam.status is not ExamStatus.DRAFT:
            raise ExamValidationError("Only draft exams can be published")

        question_ids = self._exam_repo.list_question_ids(exam_id)
        if not question_ids:
            raise ExamValidationError("Cannot publish exam without questions")

        self._exam_repo.set_status(exam_id, ExamStatus.ACTIVE)
        self._log_event_safely(
            entity_type="exam",
            entity_id=exam_id,
            actor_type="admin",
            actor_id="admin",
            event_type=ExamEventType.EXAM_PUBLISHED,
            payload={"status": ExamStatus.ACTIVE.value},
        )
        published_exam = self._exam_repo.get_exam(exam_id)
        if published_exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found after publish")
        return published_exam

    def close_exam(self, exam_id: str, actor_id: str, actor_role: str = "admin") -> Exam:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")
        if exam.status is ExamStatus.CLOSED:
            return exam
        if exam.status is ExamStatus.ARCHIVED:
            raise ExamValidationError("Archived exams are read-only")
        if exam.status is not ExamStatus.ACTIVE:
            raise ExamValidationError("Only active exams can be closed")

        self._exam_repo.set_status(exam_id, ExamStatus.CLOSED)
        closed_exam = self._exam_repo.get_exam(exam_id)
        if closed_exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found after close")

        self._exam_repo.log_exam_event(
            exam_id=exam_id,
            event_type=ExamEventType.EXAM_CLOSED,
            timestamp=utc_now_iso(),
            actor_id=actor_id,
            actor_role=actor_role,
        )
        return closed_exam

    def _log_event_safely(self, **kwargs: Any) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.log_event(**kwargs)
        except Exception:
            return

    def generate_exam_snapshot(self, exam_id: str, attempt_id: str) -> list[dict]:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")

        question_ids = self._exam_repo.list_question_ids(exam_id)
        if not question_ids:
            raise ExamValidationError("Exam has no questions")

        randomized = question_ids[:]
        random.shuffle(randomized)

        now = utc_now_iso()
        snapshot = [
            AttemptQuestionSnapshot(
                attempt_id=attempt_id,
                exam_id=exam_id,
                question_id=question_id,
                order_index=index,
                created_at=now,
            )
            for index, question_id in enumerate(randomized, start=1)
        ]

        self._exam_repo.clear_snapshot(attempt_id)
        self._exam_repo.store_snapshot(snapshot)

        return [
            {
                "attempt_id": item.attempt_id,
                "exam_id": item.exam_id,
                "question_id": item.question_id,
                "order_index": item.order_index,
            }
            for item in snapshot
        ]
