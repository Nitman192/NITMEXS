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

    def get_question_difficulty_heatmap(self, exam_id: str) -> dict:
        self._assert_exam_exists(exam_id)
        return {
            "exam_id": exam_id,
            "cells": self._analytics_repo.get_question_difficulty_heatmap(exam_id),
        }

    def get_topic_performance_heatmap(self, exam_id: str) -> dict:
        self._assert_exam_exists(exam_id)
        return {
            "exam_id": exam_id,
            "cells": self._analytics_repo.get_topic_performance_heatmap(exam_id),
        }

    def get_score_distribution(self, exam_id: str) -> dict:
        self._assert_exam_exists(exam_id)
        percentages = self._analytics_repo.get_exam_score_percentages(exam_id)

        buckets: list[dict] = [
            {"label": "<0", "range_start": None, "range_end": 0, "count": 0}
        ]
        for start in range(0, 100, 10):
            buckets.append(
                {
                    "label": f"{start}-{start + 9}",
                    "range_start": start,
                    "range_end": start + 10,
                    "count": 0,
                }
            )
        buckets.append(
            {
                "label": "100+",
                "range_start": 100,
                "range_end": None,
                "count": 0,
            }
        )

        for value in percentages:
            if value < 0:
                buckets[0]["count"] += 1
                continue
            if value >= 100:
                buckets[-1]["count"] += 1
                continue

            bucket_index = int(value // 10) + 1
            buckets[bucket_index]["count"] += 1

        return {
            "exam_id": exam_id,
            "total_attempts": len(percentages),
            "buckets": buckets,
        }

    def _assert_exam_exists(self, exam_id: str) -> None:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")
