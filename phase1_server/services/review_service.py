"""Review workflow for fill-in-the-blanks and subjective answers."""

from __future__ import annotations

from datetime import datetime, timezone

from phase1_server.models import GradingState, QuestionType, QuestionVariantDecision
from phase1_server.repositories.attempt_repository import AttemptRepository
from phase1_server.repositories.exam_repository import ExamRepository
from phase1_server.repositories.question_repository import QuestionRepository
from phase1_server.services.audit_service import AuditService
from phase1_server.services.exam_service import ExamNotFoundError
from phase1_server.services.grading_service import GradingEngine
from phase1_server.services.question_service import QuestionService


class ReviewError(ValueError):
    pass


class ReviewNotFoundError(ReviewError):
    pass


class ReviewValidationError(ReviewError):
    pass


class ReviewService:
    def __init__(
        self,
        attempt_repo: AttemptRepository,
        exam_repo: ExamRepository,
        question_repo: QuestionRepository,
        audit_service: AuditService | None = None,
    ):
        self._attempt_repo = attempt_repo
        self._exam_repo = exam_repo
        self._question_repo = question_repo
        self._audit_service = audit_service

    def list_fib_review_queue(self, exam_id: str) -> list[dict]:
        self._assert_exam(exam_id)
        return self._attempt_repo.list_fib_review_queue(exam_id)

    def apply_fib_decision(
        self,
        exam_id: str,
        question_id: str,
        normalized_text_answer: str,
        decision: str,
        canonical_answer_text: str,
        reviewer_id: str,
    ) -> dict:
        self._assert_exam(exam_id)
        question = self._question_repo.get_question(question_id)
        if question is None:
            raise ReviewNotFoundError(f"Question '{question_id}' not found")
        if question.question_type is not QuestionType.FIB_TEXT:
            raise ReviewValidationError("FIB review decisions are allowed only for fib_text questions")

        normalized = QuestionService.normalize_text_answer(normalized_text_answer)
        if not normalized:
            raise ReviewValidationError("normalized_text_answer cannot be empty")
        if decision not in {
            QuestionVariantDecision.ACCEPTED.value,
            QuestionVariantDecision.REJECTED.value,
        }:
            raise ReviewValidationError("Invalid FIB review decision")

        reviewed_at = self._now_iso()
        variant_id = self._question_repo.upsert_text_variant(
            question_id=question_id,
            answer_text=canonical_answer_text.strip(),
            normalized_answer_text=normalized,
            decision=decision,
            created_by=reviewer_id,
            created_at=reviewed_at,
        )
        impacted = self._attempt_repo.list_attempt_ids_for_pending_fib_variant(
            exam_id=exam_id,
            question_id=question_id,
            normalized_text_answer=normalized,
        )
        if not impacted:
            raise ReviewNotFoundError("No pending answers found for the selected FIB phrase")

        marks_awarded = float(question.marks) if decision == QuestionVariantDecision.ACCEPTED.value else 0.0
        is_correct = decision == QuestionVariantDecision.ACCEPTED.value
        grading_engine = GradingEngine(
            self._attempt_repo,
            self._exam_repo,
            self._question_repo,
        )
        for item in impacted:
            self._attempt_repo.update_question_result_review(
                attempt_id=item["attempt_id"],
                question_id=question_id,
                grading_state=GradingState.REVIEW_RESOLVED.value,
                marks_awarded=marks_awarded,
                is_correct=is_correct,
                matched_variant_id=variant_id,
                reviewed_by=reviewer_id,
                reviewed_at=reviewed_at,
                review_note=f"FIB response {decision}",
            )
            grading_engine.refresh_attempt_result(item["attempt_id"], reviewed_at)

        self._log_event(
            entity_type="exam",
            entity_id=exam_id,
            actor_type="admin",
            actor_id=reviewer_id,
            event_type="FIB_REVIEW_DECISION",
            payload={
                "question_id": question_id,
                "normalized_text_answer": normalized,
                "decision": decision,
                "impacted_attempt_count": len(impacted),
            },
            created_at=reviewed_at,
        )
        return {
            "exam_id": exam_id,
            "question_id": question_id,
            "normalized_text_answer": normalized,
            "decision": decision,
            "impacted_attempt_count": len(impacted),
        }

    def list_subjective_review_queue(self, exam_id: str) -> list[dict]:
        self._assert_exam(exam_id)
        return self._attempt_repo.list_subjective_review_queue(exam_id)

    def score_subjective_answer(
        self,
        attempt_id: str,
        question_id: str,
        marks_awarded: float,
        reviewer_id: str,
        review_note: str | None = None,
    ) -> dict:
        result_row = self._attempt_repo.get_question_result(attempt_id, question_id)
        if result_row is None:
            raise ReviewNotFoundError("Attempt question result not found")
        if result_row["question_type"] not in {
            QuestionType.SHORT_ANSWER.value,
            QuestionType.LONG_ANSWER.value,
        }:
            raise ReviewValidationError("Manual scoring is allowed only for short/long answers")
        if result_row["grading_state"] != GradingState.PENDING_REVIEW.value:
            raise ReviewValidationError("Question is not pending review")
        max_marks = float(result_row["max_marks"])
        if marks_awarded < 0 or marks_awarded > max_marks:
            raise ReviewValidationError("marks_awarded must be within the allowed range")
        rounded_marks = round(float(marks_awarded), 2)
        reviewed_at = self._now_iso()
        self._attempt_repo.update_question_result_review(
            attempt_id=attempt_id,
            question_id=question_id,
            grading_state=GradingState.REVIEW_RESOLVED.value,
            marks_awarded=rounded_marks,
            is_correct=rounded_marks > 0,
            matched_variant_id=None,
            reviewed_by=reviewer_id,
            reviewed_at=reviewed_at,
            review_note=review_note,
        )
        grading_engine = GradingEngine(
            self._attempt_repo,
            self._exam_repo,
            self._question_repo,
        )
        summary = grading_engine.refresh_attempt_result(attempt_id, reviewed_at)
        self._log_event(
            entity_type="attempt",
            entity_id=attempt_id,
            actor_type="admin",
            actor_id=reviewer_id,
            event_type="SUBJECTIVE_REVIEW_SCORED",
            payload={
                "question_id": question_id,
                "marks_awarded": rounded_marks,
                "review_note": review_note,
                "result_ready": summary.result_ready,
            },
            created_at=reviewed_at,
        )
        return {
            "attempt_id": attempt_id,
            "question_id": question_id,
            "marks_awarded": rounded_marks,
            "result_ready": summary.result_ready,
            "pending_review_count": summary.pending_review_count,
        }

    def _assert_exam(self, exam_id: str) -> None:
        if self._exam_repo.get_exam(exam_id) is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")

    def _log_event(self, **kwargs) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.log_event(**kwargs)
        except Exception:
            return

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
