"""Read-only analytics service for institutional reporting."""

from __future__ import annotations

from phase1_server.repositories.analytics_repository import AnalyticsRepository
from phase1_server.repositories.exam_repository import ExamRepository
from phase1_server.services.exam_service import ExamNotFoundError


class AnalyticsService:
    def __init__(self, analytics_repo: AnalyticsRepository, exam_repo: ExamRepository):
        self._analytics_repo = analytics_repo
        self._exam_repo = exam_repo

    def get_exam_analytics(self, exam_id: str) -> dict:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")

        question_rows = self._analytics_repo.get_exam_item_statistics(exam_id)
        summary = self._analytics_repo.get_exam_summary(exam_id)

        return {
            "exam_id": exam_id,
            "question_metrics": question_rows,
            "summary": {
                "mean_score": summary["mean_score"],
                "pass_rate": summary["pass_rate"],
                "total_attempts": summary["total_attempts"],
            },
        }

    def get_student_performance(self, student_id: str) -> dict:
        return self._analytics_repo.get_student_performance(student_id)
