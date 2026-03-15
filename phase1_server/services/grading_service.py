"""Grading engine for objective and review-based text questions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phase1_server.models import AttemptStatus, GradingState, QuestionType, QuestionVariantDecision
from phase1_server.repositories.analytics_repository import AnalyticsRepository
from phase1_server.repositories.attempt_repository import AttemptRepository
from phase1_server.repositories.exam_repository import ExamRepository
from phase1_server.repositories.question_repository import QuestionRepository


class GradingError(ValueError):
    pass


class GradingNotFoundError(GradingError):
    pass


class GradingOwnershipError(GradingError):
    pass


class ResultNotReadyError(GradingError):
    pass


@dataclass(frozen=True)
class GradingSummary:
    attempt_id: str
    total_score: float
    total_possible_marks: float
    percentage: float
    passed: bool
    graded_now: bool
    pending_review_count: int
    result_ready: bool


class GradingEngine:
    def __init__(
        self,
        attempt_repo: AttemptRepository,
        exam_repo: ExamRepository,
        question_repo: QuestionRepository,
        analytics_repo: AnalyticsRepository | None = None,
    ):
        self._attempt_repo = attempt_repo
        self._exam_repo = exam_repo
        self._question_repo = question_repo
        self._analytics_repo = analytics_repo

    def grade_attempt(self, attempt_id: str, graded_at: str) -> GradingSummary:
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise GradingNotFoundError(f"Attempt '{attempt_id}' not found")
        if attempt.status != AttemptStatus.FINALIZED:
            raise GradingError("Attempt must be finalized before grading")

        if self._attempt_repo.result_exists(attempt_id):
            return self._summary_from_saved_result(attempt_id)

        existing_rows = self._attempt_repo.get_question_results(attempt_id)
        if existing_rows:
            return self.refresh_attempt_result(attempt_id, graded_at, graded_now=False)

        exam = self._exam_repo.get_exam(attempt.exam_id)
        if exam is None:
            raise GradingNotFoundError(f"Exam '{attempt.exam_id}' not found")

        question_ids = self._attempt_repo.list_snapshot_question_ids(attempt_id)
        responses = self._attempt_repo.get_responses(attempt_id)

        self._attempt_repo.clear_results(attempt_id)

        for question_id in question_ids:
            question = self._question_repo.get_question(question_id)
            if question is None:
                raise GradingError(f"Question '{question_id}' is missing")

            response = responses.get(question_id, {})
            self._save_initial_question_result(
                exam_negative_marking=exam.negative_marking,
                attempt_id=attempt_id,
                question=question,
                response=response,
            )

        return self.refresh_attempt_result(attempt_id, graded_at, graded_now=True)

    def refresh_attempt_result(
        self,
        attempt_id: str,
        graded_at: str,
        graded_now: bool = False,
    ) -> GradingSummary:
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise GradingNotFoundError(f"Attempt '{attempt_id}' not found")
        exam = self._exam_repo.get_exam(attempt.exam_id)
        if exam is None:
            raise GradingNotFoundError(f"Exam '{attempt.exam_id}' not found")

        rows = self._attempt_repo.get_question_results(attempt_id)
        pending_review_count = sum(
            1
            for row in rows
            if row["grading_state"] == GradingState.PENDING_REVIEW.value
        )
        total_score = float(sum(float(row["marks_awarded"] or 0.0) for row in rows))
        total_possible_marks = float(sum(float(row["max_marks"] or 0.0) for row in rows))

        if pending_review_count > 0:
            self._attempt_repo.delete_attempt_result(attempt_id)
            return GradingSummary(
                attempt_id=attempt_id,
                total_score=total_score,
                total_possible_marks=total_possible_marks,
                percentage=0.0,
                passed=False,
                graded_now=graded_now,
                pending_review_count=pending_review_count,
                result_ready=False,
            )

        percentage = (
            (total_score / total_possible_marks) * 100 if total_possible_marks > 0 else 0.0
        )
        passed = percentage >= exam.passing_percentage
        self._attempt_repo.save_attempt_result(
            attempt_id=attempt_id,
            total_score=total_score,
            total_possible_marks=total_possible_marks,
            percentage=percentage,
            passed=passed,
            graded_at=graded_at,
        )
        return GradingSummary(
            attempt_id=attempt_id,
            total_score=total_score,
            total_possible_marks=total_possible_marks,
            percentage=percentage,
            passed=passed,
            graded_now=graded_now,
            pending_review_count=0,
            result_ready=True,
        )

    def get_result(self, attempt_id: str, student_id: str) -> dict:
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise GradingNotFoundError(f"Attempt '{attempt_id}' not found")
        if attempt.candidate_id != student_id:
            raise GradingOwnershipError("Attempt does not belong to student")
        if attempt.status != AttemptStatus.FINALIZED:
            raise ResultNotReadyError("Result available only after attempt finalization")

        summary = self._attempt_repo.get_attempt_result(attempt_id)
        if summary is None:
            raise ResultNotReadyError("Result not available yet")

        return {
            **summary,
            "exam_id": attempt.exam_id,
            "question_results": self._build_enriched_question_results(attempt_id),
        }

    def get_admin_result(self, attempt_id: str) -> dict:
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise GradingNotFoundError(f"Attempt '{attempt_id}' not found")
        if attempt.status != AttemptStatus.FINALIZED:
            raise ResultNotReadyError("Result available only after attempt finalization")

        summary = self._attempt_repo.get_attempt_result(attempt_id)
        if summary is None:
            raise ResultNotReadyError("Result not available yet")

        return {
            **summary,
            "attempt_id": attempt_id,
            "student_id": attempt.candidate_id,
            "exam_id": attempt.exam_id,
            "question_results": self._build_enriched_question_results(attempt_id),
        }

    def _save_initial_question_result(
        self,
        exam_negative_marking: float,
        attempt_id: str,
        question,
        response: dict,
    ) -> None:
        question_type = question.question_type
        marks = float(question.marks)
        selected_option_id = response.get("selected_option_id")
        text_answer = response.get("text_answer")
        normalized_text_answer = response.get("normalized_text_answer")
        correct_option_id = None
        matched_variant_id = None
        grading_state = GradingState.AUTO_INCORRECT.value
        marks_awarded = 0.0
        is_correct = False

        if question_type in {QuestionType.MCQ_SINGLE, QuestionType.TRUE_FALSE}:
            correct_option_id = self._question_repo.get_correct_option_id(question.id)
            if correct_option_id is None:
                raise GradingError(f"Question '{question.id}' is missing the correct option")
            if selected_option_id == correct_option_id:
                grading_state = GradingState.AUTO_CORRECT.value
                marks_awarded = marks
                is_correct = True
            elif selected_option_id and question_type is QuestionType.MCQ_SINGLE:
                marks_awarded = -float(exam_negative_marking) if exam_negative_marking > 0 else 0.0
        elif question_type is QuestionType.FIB_TEXT:
            if text_answer and normalized_text_answer:
                variant = self._question_repo.get_text_variant_by_normalized(
                    question.id,
                    normalized_text_answer,
                )
                if variant is None:
                    grading_state = GradingState.PENDING_REVIEW.value
                else:
                    matched_variant_id = variant.id
                    if variant.decision is QuestionVariantDecision.ACCEPTED:
                        grading_state = GradingState.AUTO_CORRECT.value
                        marks_awarded = marks
                        is_correct = True
                    else:
                        grading_state = GradingState.AUTO_INCORRECT.value
        else:
            if text_answer:
                grading_state = GradingState.PENDING_REVIEW.value

        self._attempt_repo.save_question_result(
            attempt_id=attempt_id,
            question_id=question.id,
            question_type=question_type.value,
            selected_option_id=selected_option_id,
            correct_option_id=correct_option_id,
            text_answer=text_answer,
            matched_variant_id=matched_variant_id,
            grading_state=grading_state,
            marks_awarded=marks_awarded,
            max_marks=marks,
            is_correct=is_correct,
        )

        if self._analytics_repo is not None and grading_state != GradingState.PENDING_REVIEW.value:
            try:
                self._analytics_repo.upsert_item_stat(
                    exam_id=self._attempt_repo.get(attempt_id).exam_id,  # type: ignore[union-attr]
                    question_id=question.id,
                    is_correct=is_correct,
                    marks_awarded=marks_awarded,
                )
            except Exception:
                pass

    def _summary_from_saved_result(self, attempt_id: str) -> GradingSummary:
        existing = self._attempt_repo.get_attempt_result(attempt_id)
        if existing is None:
            raise GradingError("Result existence check failed")
        return GradingSummary(
            attempt_id=attempt_id,
            total_score=existing["total_score"],
            total_possible_marks=existing["total_possible_marks"],
            percentage=existing["percentage"],
            passed=existing["passed"],
            graded_now=False,
            pending_review_count=0,
            result_ready=True,
        )

    def _build_enriched_question_results(self, attempt_id: str) -> list[dict[str, Any]]:
        snapshot_question_ids = self._attempt_repo.list_snapshot_question_ids(attempt_id)
        sequence_map = {
            question_id: index for index, question_id in enumerate(snapshot_question_ids, start=1)
        }
        rows = self._attempt_repo.get_question_results(attempt_id)
        responses = self._attempt_repo.get_responses(attempt_id)
        enriched: list[dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            record["sequence_number"] = sequence_map.get(row["question_id"])
            record["status"] = self._result_status(row)

            question_bundle = self._question_repo.get_question_with_options(row["question_id"])
            if question_bundle is not None:
                question, options = question_bundle
                option_text_by_id = {option.id: option.option_text for option in options}
                response = responses.get(row["question_id"], {})
                record.update(
                    {
                        "question_text": question.text,
                        "topic": question.topic,
                        "difficulty": question.difficulty,
                        "question_type": question.question_type.value,
                        "word_policy": {
                            "word_target_min": question.word_target_min,
                            "word_target_max": question.word_target_max,
                            "word_hard_max": question.word_hard_max,
                        },
                        "selected_option_text": option_text_by_id.get(row["selected_option_id"]),
                        "correct_option_text": option_text_by_id.get(row["correct_option_id"]),
                        "text_answer": record.get("text_answer") or response.get("text_answer"),
                        "word_count": response.get("word_count"),
                    }
                )
            enriched.append(record)
        return enriched

    def _result_status(self, row: dict[str, Any]) -> str:
        question_type = row.get("question_type")
        if row.get("grading_state") == GradingState.PENDING_REVIEW.value:
            return "pending_review"
        if question_type in {QuestionType.MCQ_SINGLE.value, QuestionType.TRUE_FALSE.value}:
            if not row.get("selected_option_id"):
                return "skipped"
            return "correct" if row.get("is_correct") else "incorrect"
        if not row.get("text_answer"):
            return "skipped"
        return "correct" if row.get("is_correct") else "incorrect"
