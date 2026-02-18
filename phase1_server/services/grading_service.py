"""Objective grading engine for finalized attempts."""

from __future__ import annotations

from dataclasses import dataclass

from phase1_server.models import AttemptStatus
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


class GradingEngine:
    def __init__(
        self,
        attempt_repo: AttemptRepository,
        exam_repo: ExamRepository,
        question_repo: QuestionRepository,
    ):
        self._attempt_repo = attempt_repo
        self._exam_repo = exam_repo
        self._question_repo = question_repo

    def grade_attempt(self, attempt_id: str, graded_at: str) -> GradingSummary:
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise GradingNotFoundError(f"Attempt '{attempt_id}' not found")
        if attempt.status != AttemptStatus.FINALIZED:
            raise GradingError("Attempt must be finalized before grading")

        if self._attempt_repo.result_exists(attempt_id):
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
            )

        exam = self._exam_repo.get_exam(attempt.exam_id)
        if exam is None:
            raise GradingNotFoundError(f"Exam '{attempt.exam_id}' not found")

        question_ids = self._attempt_repo.list_snapshot_question_ids(attempt_id)
        responses = self._attempt_repo.get_responses(attempt_id)

        total_score = 0.0
        total_possible_marks = 0.0

        self._attempt_repo.clear_results(attempt_id)

        for question_id in question_ids:
            marks = self._question_repo.get_question_marks(question_id)
            correct_option_id = self._question_repo.get_correct_option_id(question_id)
            if marks is None or correct_option_id is None:
                raise GradingError(f"Question '{question_id}' is missing grading metadata")

            selected_option_id = responses.get(question_id)
            total_possible_marks += marks

            if selected_option_id is None:
                awarded = 0.0
                is_correct = False
            elif selected_option_id == correct_option_id:
                awarded = float(marks)
                is_correct = True
            else:
                awarded = -float(exam.negative_marking) if exam.negative_marking > 0 else 0.0
                is_correct = False

            total_score += awarded
            self._attempt_repo.save_question_result(
                attempt_id=attempt_id,
                question_id=question_id,
                selected_option_id=selected_option_id,
                correct_option_id=correct_option_id,
                marks_awarded=awarded,
                max_marks=marks,
                is_correct=is_correct,
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
            graded_now=True,
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
            "question_results": self._attempt_repo.get_question_results(attempt_id),
        }
