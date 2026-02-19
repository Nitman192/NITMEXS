"""Repository for lightweight system metrics."""

from __future__ import annotations

import sqlite3
from typing import Protocol


class MetricsRepository(Protocol):
    def record_duration(self, metric_name: str, metric_key: str, duration_ms: float, updated_at: str) -> None: ...

    def increment_counter(self, metric_name: str, metric_key: str, delta: int, updated_at: str) -> None: ...

    def list_metrics(self) -> list[dict]: ...


class SQLiteMetricsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def record_duration(
        self,
        metric_name: str,
        metric_key: str,
        duration_ms: float,
        updated_at: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO system_metrics(
                metric_name, metric_key, count, total_value, max_value, updated_at
            ) VALUES(?, ?, 1, ?, ?, ?)
            ON CONFLICT(metric_name, metric_key)
            DO UPDATE SET count = system_metrics.count + 1,
                          total_value = system_metrics.total_value + excluded.total_value,
                          max_value = MAX(system_metrics.max_value, excluded.max_value),
                          updated_at = excluded.updated_at
            """,
            (metric_name, metric_key, duration_ms, duration_ms, updated_at),
        )

    def increment_counter(
        self,
        metric_name: str,
        metric_key: str,
        delta: int,
        updated_at: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO system_metrics(
                metric_name, metric_key, count, total_value, max_value, updated_at
            ) VALUES(?, ?, ?, 0, 0, ?)
            ON CONFLICT(metric_name, metric_key)
            DO UPDATE SET count = system_metrics.count + excluded.count,
                          updated_at = excluded.updated_at
            """,
            (metric_name, metric_key, delta, updated_at),
        )

    def list_metrics(self) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT metric_name, metric_key, count, total_value, max_value, updated_at
            FROM system_metrics
            ORDER BY metric_name ASC, metric_key ASC
            """
        ).fetchall()
        return [
            {
                "metric_name": row["metric_name"],
                "metric_key": row["metric_key"],
                "count": int(row["count"]),
                "total_value": float(row["total_value"]),
                "max_value": float(row["max_value"]),
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]
