"""Service layer for system metrics recording and reporting."""

from __future__ import annotations

from phase1_server.models import utc_now_iso
from phase1_server.repositories.metrics_repository import MetricsRepository


class MetricsService:
    def __init__(self, metrics_repo: MetricsRepository):
        self._metrics_repo = metrics_repo

    def record_request_duration(self, endpoint: str, duration_ms: float) -> None:
        self._metrics_repo.record_duration(
            metric_name="request_duration_ms",
            metric_key=endpoint,
            duration_ms=duration_ms,
            updated_at=utc_now_iso(),
        )

    def record_finalize_to_grade_duration(self, duration_ms: float) -> None:
        self._metrics_repo.record_duration(
            metric_name="finalize_to_grade_ms",
            metric_key="finalize",
            duration_ms=duration_ms,
            updated_at=utc_now_iso(),
        )

    def increment_concurrency_conflict(self) -> None:
        self._metrics_repo.increment_counter(
            metric_name="concurrency_conflict_count",
            metric_key="attempt_state_transition",
            delta=1,
            updated_at=utc_now_iso(),
        )

    def increment_auto_expire(self) -> None:
        self._metrics_repo.increment_counter(
            metric_name="auto_expire_count",
            metric_key="attempt",
            delta=1,
            updated_at=utc_now_iso(),
        )

    def get_metrics(self) -> dict:
        rows = self._metrics_repo.list_metrics()
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            item = {
                "key": row["metric_key"],
                "count": row["count"],
                "total_value": row["total_value"],
                "max_value": row["max_value"],
                "updated_at": row["updated_at"],
            }
            grouped.setdefault(row["metric_name"], []).append(item)
        return grouped
