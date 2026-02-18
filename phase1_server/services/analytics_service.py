"""Read-only analytics service computed from persisted grading results."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median, pstdev

from phase1_server.repositories.attempt_repository import AttemptRepository
from phase1_server.repositories.exam_repository import ExamRepository
from phase1_server.services.exam_service import ExamNotFoundError


@dataclass(frozen=True)
class ExamAnalyticsSummary:
    mean_score: float
    median_score: float
    pass_rate: float
    standard_deviation: float


class AnalyticsService:
    def __init__(self, attempt_repo: AttemptRepository, exam_repo: ExamRepository):
        self._attempt_repo = attempt_repo
        self._exam_repo = exam_repo

    def get_exam_analytics(self, exam_id: str) -> dict:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")

        question_rows = self._attempt_repo.get_exam_question_analytics(exam_id)
        score_rows = self._attempt_repo.get_exam_attempt_scores(exam_id)

        scores = [row["total_score"] for row in score_rows]
        pass_count = sum(1 for row in score_rows if row["passed"])
        total = len(score_rows)

        summary = ExamAnalyticsSummary(
            mean_score=mean(scores) if scores else 0.0,
            median_score=median(scores) if scores else 0.0,
            pass_rate=((pass_count / total) * 100.0) if total else 0.0,
            standard_deviation=pstdev(scores) if len(scores) > 1 else 0.0,
        )

        return {
            "exam_id": exam_id,
            "question_metrics": [
                {
                    "question_id": row["question_id"],
                    "difficulty_index": row["difficulty_index"],
                    "average_score": row["average_score"],
                    "total_attempts": row["total_attempts"],
                }
                for row in question_rows
            ],
            "summary": {
                "mean_score": summary.mean_score,
                "median_score": summary.median_score,
                "pass_rate": summary.pass_rate,
                "standard_deviation": summary.standard_deviation,
            },
        }
