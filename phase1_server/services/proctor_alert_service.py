"""Service for persistent suspicious-behavior alert lifecycle management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from phase1_server.repositories.exam_repository import ExamRepository
from phase1_server.repositories.proctor_alert_repository import ProctorAlertRepository
from phase1_server.services.audit_service import AuditService
from phase1_server.services.metrics_service import MetricsService
from phase1_server.services.proctoring_service import (
    ProctoringService,
    ProctoringValidationError,
)
from phase1_server.services.exam_service import ExamNotFoundError


class ProctorAlertValidationError(ValueError):
    pass


class ProctorAlertNotFoundError(LookupError):
    pass


class ProctorAlertService:
    VALID_STATUSES = {"open", "acknowledged", "resolved"}

    def __init__(
        self,
        alert_repo: ProctorAlertRepository,
        exam_repo: ExamRepository,
        proctoring_service: ProctoringService,
        audit_service: AuditService | None = None,
        metrics_service: MetricsService | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ):
        self._alert_repo = alert_repo
        self._exam_repo = exam_repo
        self._proctoring_service = proctoring_service
        self._audit_service = audit_service
        self._metrics_service = metrics_service
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def sync_alerts(
        self,
        exam_id: str | None = None,
        active_limit: int = 500,
        triggered_by: str = "admin",
    ) -> dict:
        if exam_id is not None:
            self._assert_exam_exists(exam_id)
        if not triggered_by.strip():
            raise ProctorAlertValidationError("triggered_by must not be empty")

        try:
            if exam_id is None:
                snapshot = self._proctoring_service.get_dashboard(
                    active_limit=active_limit,
                    finalize_limit=1,
                )
            else:
                snapshot = self._proctoring_service.get_live_status(exam_id)
        except ProctoringValidationError as exc:
            raise ProctorAlertValidationError(str(exc)) from exc

        active_attempts = snapshot["active_attempts"]
        suspicious = snapshot["suspicious_indicators"]
        attempt_map = {item["attempt_id"]: item for item in active_attempts}
        active_attempt_ids = {item["attempt_id"] for item in active_attempts}
        suspicious_keys: set[tuple[str, str]] = {
            (indicator["attempt_id"], flag)
            for indicator in suspicious
            for flag in indicator["flags"]
        }

        created_count = 0
        updated_count = 0
        alerts: list[dict] = []
        for indicator in suspicious:
            attempt_id = indicator["attempt_id"]
            attempt_snapshot = attempt_map.get(attempt_id, {})
            for flag in indicator["flags"]:
                alert_payload, is_new = self._alert_repo.upsert_open_alert(
                    attempt_id=attempt_id,
                    exam_id=indicator["exam_id"],
                    student_id=indicator["student_id"],
                    indicator_code=flag,
                    indicator_payload={
                        "flag": flag,
                        "remaining_seconds": attempt_snapshot.get("remaining_seconds"),
                        "elapsed_seconds": attempt_snapshot.get("elapsed_seconds"),
                        "answered_question_count": attempt_snapshot.get(
                            "answered_question_count"
                        ),
                        "total_question_count": attempt_snapshot.get("total_question_count"),
                        "progress_percent": attempt_snapshot.get("progress_percent"),
                    },
                    detected_at=snapshot["as_of"],
                )
                if is_new:
                    created_count += 1
                    self._log_alert_raised(
                        attempt_id=alert_payload["attempt_id"],
                        alert_id=alert_payload["id"],
                        flag=flag,
                        exam_id=alert_payload["exam_id"],
                        student_id=alert_payload["student_id"],
                        triggered_by=triggered_by,
                    )
                    self._record_raised_metrics(flag)
                else:
                    updated_count += 1
                alerts.append(alert_payload)

        auto_resolved_count = 0
        auto_resolved_alert_ids: list[str] = []
        unresolved_alerts = self._alert_repo.list_unresolved_alerts_for_sync(exam_id=exam_id)
        for alert in unresolved_alerts:
            alert_key = (alert["attempt_id"], alert["indicator_code"])
            if alert_key in suspicious_keys:
                continue

            reason = (
                "attempt_not_active"
                if alert["attempt_id"] not in active_attempt_ids
                else "indicator_cleared"
            )
            note = f"auto_resolved_{reason}"
            resolved = self._alert_repo.resolve_alert(
                alert_id=alert["id"],
                actor_id="system",
                resolved_at=snapshot["as_of"],
                resolution_note=note,
            )
            if resolved is None or resolved["status"] != "resolved":
                continue

            auto_resolved_count += 1
            auto_resolved_alert_ids.append(resolved["id"])
            self._log_alert_auto_resolved(
                attempt_id=resolved["attempt_id"],
                alert_id=resolved["id"],
                indicator_code=resolved["indicator_code"],
                triggered_by=triggered_by,
                reason=reason,
            )
            self._record_resolved_metrics(resolved, auto_resolved=True)

        return {
            "exam_id": exam_id,
            "as_of": snapshot["as_of"],
            "active_attempt_count": len(active_attempts),
            "suspicious_attempt_count": len(suspicious),
            "created_count": created_count,
            "updated_count": updated_count,
            "auto_resolved_count": auto_resolved_count,
            "alert_count": len(alerts),
            "alerts": alerts,
            "auto_resolved_alert_ids": auto_resolved_alert_ids,
        }

    def list_alerts(
        self,
        exam_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> dict:
        if exam_id is not None:
            self._assert_exam_exists(exam_id)
        if limit < 1 or limit > 1000:
            raise ProctorAlertValidationError("limit must be between 1 and 1000")
        if status is not None and status not in self.VALID_STATUSES:
            raise ProctorAlertValidationError(
                "status must be one of: open, acknowledged, resolved"
            )

        alerts = self._alert_repo.list_alerts(exam_id=exam_id, status=status, limit=limit)
        return {
            "exam_id": exam_id,
            "status": status,
            "count": len(alerts),
            "alerts": alerts,
        }

    def get_alert_summary(self, exam_id: str | None = None) -> dict:
        if exam_id is not None:
            self._assert_exam_exists(exam_id)
        summary = self._alert_repo.get_alert_summary(exam_id=exam_id)
        return {"exam_id": exam_id, "summary": summary}

    def get_live_alerts(self, exam_id: str | None = None, limit: int = 200) -> dict:
        if exam_id is not None:
            self._assert_exam_exists(exam_id)
        if limit < 1 or limit > 1000:
            raise ProctorAlertValidationError("limit must be between 1 and 1000")

        summary = self._alert_repo.get_alert_summary(exam_id=exam_id)
        alerts = self._alert_repo.list_unresolved_alerts(exam_id=exam_id, limit=limit)
        return {
            "exam_id": exam_id,
            "as_of": self._normalize_dt(self._now_provider()).isoformat(),
            "count": len(alerts),
            "alerts": alerts,
            "summary": summary,
        }

    def get_operational_metrics(
        self,
        exam_id: str | None = None,
        stale_after_minutes: int = 15,
    ) -> dict:
        if exam_id is not None:
            self._assert_exam_exists(exam_id)
        if stale_after_minutes < 1 or stale_after_minutes > 10080:
            raise ProctorAlertValidationError(
                "stale_after_minutes must be between 1 and 10080"
            )

        now = self._normalize_dt(self._now_provider())
        stale_before = now - timedelta(minutes=stale_after_minutes)
        summary = self._alert_repo.get_alert_summary(exam_id=exam_id)
        unresolved = self._alert_repo.list_unresolved_alerts_for_sync(exam_id=exam_id)
        all_alerts = self._alert_repo.list_alerts_for_metrics(exam_id=exam_id)

        stale_unresolved_count = 0
        max_unresolved_age_seconds = 0.0
        for alert in unresolved:
            last_detected = self._parse_iso(alert["last_detected_at"])
            if last_detected is None:
                continue
            age_seconds = max(0.0, (now - last_detected).total_seconds())
            if age_seconds > max_unresolved_age_seconds:
                max_unresolved_age_seconds = age_seconds
            if last_detected < stale_before:
                stale_unresolved_count += 1

        acknowledge_seconds: list[float] = []
        resolution_seconds: list[float] = []
        for alert in all_alerts:
            created_at = self._parse_iso(alert["created_at"])
            acknowledged_at = self._parse_iso(alert["acknowledged_at"])
            resolved_at = self._parse_iso(alert["resolved_at"])

            if (
                created_at is not None
                and acknowledged_at is not None
                and acknowledged_at >= created_at
            ):
                acknowledge_seconds.append((acknowledged_at - created_at).total_seconds())
            if created_at is not None and resolved_at is not None and resolved_at >= created_at:
                resolution_seconds.append((resolved_at - created_at).total_seconds())

        unresolved_count = summary["open_count"] + summary["acknowledged_count"]
        return {
            "exam_id": exam_id,
            "as_of": now.isoformat(),
            "stale_after_minutes": stale_after_minutes,
            "summary": summary,
            "kpis": {
                "unresolved_count": unresolved_count,
                "stale_unresolved_count": stale_unresolved_count,
                "max_unresolved_age_seconds": max_unresolved_age_seconds,
                "acknowledged_samples": len(acknowledge_seconds),
                "resolved_samples": len(resolution_seconds),
                "average_acknowledge_seconds": self._mean(acknowledge_seconds),
                "average_resolution_seconds": self._mean(resolution_seconds),
                "p95_acknowledge_seconds": self._percentile(
                    acknowledge_seconds,
                    0.95,
                ),
                "p95_resolution_seconds": self._percentile(
                    resolution_seconds,
                    0.95,
                ),
            },
        }

    def acknowledge_alert(self, alert_id: str, actor_id: str = "admin") -> dict:
        if not alert_id.strip():
            raise ProctorAlertValidationError("alert_id must not be empty")
        if not actor_id.strip():
            raise ProctorAlertValidationError("actor_id must not be empty")

        current = self._alert_repo.get_alert(alert_id)
        if current is None:
            raise ProctorAlertNotFoundError(f"Proctor alert '{alert_id}' not found")
        if current["status"] == "resolved":
            raise ProctorAlertValidationError("Resolved alert cannot be acknowledged")

        acknowledged = self._alert_repo.acknowledge_alert(
            alert_id=alert_id,
            actor_id=actor_id,
            acknowledged_at=self._normalize_dt(self._now_provider()).isoformat(),
        )
        if acknowledged is None:
            raise ProctorAlertNotFoundError(f"Proctor alert '{alert_id}' not found")

        changed = current["status"] != acknowledged["status"]
        if changed:
            self._log_alert_acknowledged(
                attempt_id=acknowledged["attempt_id"],
                alert_id=acknowledged["id"],
                indicator_code=acknowledged["indicator_code"],
                actor_id=actor_id,
            )
            self._record_acknowledged_metrics(acknowledged)
        return {"changed": changed, "alert": acknowledged}

    def resolve_alert(
        self,
        alert_id: str,
        actor_id: str = "admin",
        note: str | None = None,
    ) -> dict:
        if not alert_id.strip():
            raise ProctorAlertValidationError("alert_id must not be empty")
        if not actor_id.strip():
            raise ProctorAlertValidationError("actor_id must not be empty")
        if note is not None and len(note) > 500:
            raise ProctorAlertValidationError("note must be <= 500 characters")

        current = self._alert_repo.get_alert(alert_id)
        if current is None:
            raise ProctorAlertNotFoundError(f"Proctor alert '{alert_id}' not found")

        resolved = self._alert_repo.resolve_alert(
            alert_id=alert_id,
            actor_id=actor_id,
            resolved_at=self._normalize_dt(self._now_provider()).isoformat(),
            resolution_note=note,
        )
        if resolved is None:
            raise ProctorAlertNotFoundError(f"Proctor alert '{alert_id}' not found")

        changed = current["status"] != resolved["status"]
        if changed:
            self._log_alert_resolved(
                attempt_id=resolved["attempt_id"],
                alert_id=resolved["id"],
                indicator_code=resolved["indicator_code"],
                actor_id=actor_id,
                note=note,
            )
            self._record_resolved_metrics(resolved, auto_resolved=False)
        return {"changed": changed, "alert": resolved}

    def _assert_exam_exists(self, exam_id: str) -> None:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")

    def _log_alert_raised(
        self,
        attempt_id: str,
        alert_id: str,
        flag: str,
        exam_id: str,
        student_id: str,
        triggered_by: str,
    ) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.log_event(
                entity_type="attempt",
                entity_id=attempt_id,
                actor_type="system",
                actor_id="proctor-alert-engine",
                event_type="PROCTOR_ALERT_RAISED",
                payload={
                    "alert_id": alert_id,
                    "flag": flag,
                    "exam_id": exam_id,
                    "student_id": student_id,
                    "triggered_by": triggered_by,
                },
            )
        except Exception:
            return

    def _log_alert_acknowledged(
        self,
        attempt_id: str,
        alert_id: str,
        indicator_code: str,
        actor_id: str,
    ) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.log_event(
                entity_type="attempt",
                entity_id=attempt_id,
                actor_type="admin",
                actor_id=actor_id,
                event_type="PROCTOR_ALERT_ACKNOWLEDGED",
                payload={
                    "alert_id": alert_id,
                    "indicator_code": indicator_code,
                },
            )
        except Exception:
            return

    def _log_alert_resolved(
        self,
        attempt_id: str,
        alert_id: str,
        indicator_code: str,
        actor_id: str,
        note: str | None,
    ) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.log_event(
                entity_type="attempt",
                entity_id=attempt_id,
                actor_type="admin",
                actor_id=actor_id,
                event_type="PROCTOR_ALERT_RESOLVED",
                payload={
                    "alert_id": alert_id,
                    "indicator_code": indicator_code,
                    "note": note,
                },
            )
        except Exception:
            return

    def _log_alert_auto_resolved(
        self,
        attempt_id: str,
        alert_id: str,
        indicator_code: str,
        triggered_by: str,
        reason: str,
    ) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.log_event(
                entity_type="attempt",
                entity_id=attempt_id,
                actor_type="system",
                actor_id="proctor-alert-engine",
                event_type="PROCTOR_ALERT_AUTO_RESOLVED",
                payload={
                    "alert_id": alert_id,
                    "indicator_code": indicator_code,
                    "triggered_by": triggered_by,
                    "reason": reason,
                },
            )
        except Exception:
            return

    def _record_raised_metrics(self, indicator_code: str) -> None:
        if self._metrics_service is None:
            return
        try:
            self._metrics_service.increment_proctor_alert_raised(indicator_code)
        except Exception:
            return

    def _record_acknowledged_metrics(self, alert: dict) -> None:
        if self._metrics_service is None:
            return
        try:
            self._metrics_service.increment_proctor_alert_acknowledged(
                alert["indicator_code"]
            )
            created_at = self._parse_iso(alert["created_at"])
            acknowledged_at = self._parse_iso(alert["acknowledged_at"])
            if (
                created_at is not None
                and acknowledged_at is not None
                and acknowledged_at >= created_at
            ):
                self._metrics_service.record_proctor_alert_ack_duration(
                    (acknowledged_at - created_at).total_seconds() * 1000.0
                )
        except Exception:
            return

    def _record_resolved_metrics(self, alert: dict, auto_resolved: bool) -> None:
        if self._metrics_service is None:
            return
        try:
            self._metrics_service.increment_proctor_alert_resolved(
                alert["indicator_code"],
                auto_resolved=auto_resolved,
            )
            created_at = self._parse_iso(alert["created_at"])
            resolved_at = self._parse_iso(alert["resolved_at"])
            if created_at is not None and resolved_at is not None and resolved_at >= created_at:
                self._metrics_service.record_proctor_alert_resolution_duration(
                    (resolved_at - created_at).total_seconds() * 1000.0
                )
        except Exception:
            return

    @staticmethod
    def _normalize_dt(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _parse_iso(value: str | None) -> datetime | None:
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _mean(values: list[float]) -> float | None:
        if not values:
            return None
        return sum(values) / len(values)

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float | None:
        if not values:
            return None
        sorted_values = sorted(values)
        index = int(round((len(sorted_values) - 1) * percentile))
        index = min(max(index, 0), len(sorted_values) - 1)
        return sorted_values[index]
