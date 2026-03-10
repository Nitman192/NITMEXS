"""Read-side service for proctor dashboard live monitoring endpoints."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Callable

from phase1_server.repositories.attempt_repository import AttemptRepository
from phase1_server.repositories.exam_repository import ExamRepository
from phase1_server.services.exam_service import ExamNotFoundError


class ProctoringValidationError(ValueError):
    pass


class ProctoringService:
    def __init__(
        self,
        attempt_repo: AttemptRepository,
        exam_repo: ExamRepository,
        now_provider: Callable[[], datetime] | None = None,
    ):
        self._attempt_repo = attempt_repo
        self._exam_repo = exam_repo
        self._now_provider = now_provider or (lambda: datetime.now(timezone.utc))

    def get_active_attempts(self, exam_id: str) -> list[dict]:
        self._assert_exam_exists(exam_id)
        now = self._normalize_dt(self._now_provider())
        return self._build_active_attempts(exam_id, now)

    def get_live_status(self, exam_id: str) -> dict:
        self._assert_exam_exists(exam_id)
        now = self._normalize_dt(self._now_provider())
        active_attempts = self._build_active_attempts(exam_id, now)
        suspicious_indicators = self._build_suspicious_indicators(active_attempts)
        finalize_events = self._attempt_repo.list_recent_finalize_events(exam_id, limit=20)

        return {
            "exam_id": exam_id,
            "as_of": now.isoformat(),
            "active_attempt_count": len(active_attempts),
            "active_attempts": active_attempts,
            "suspicious_indicators": suspicious_indicators,
            "recent_finalize_events": finalize_events,
        }

    def get_dashboard(self, active_limit: int = 200, finalize_limit: int = 50) -> dict:
        if active_limit < 1 or active_limit > 1000:
            raise ProctoringValidationError("active_limit must be between 1 and 1000")
        if finalize_limit < 1 or finalize_limit > 500:
            raise ProctoringValidationError("finalize_limit must be between 1 and 500")

        now = self._normalize_dt(self._now_provider())
        rows = self._attempt_repo.list_active_attempts(limit=active_limit)
        active_attempts = [self._active_attempt_payload(row, now) for row in rows]
        suspicious_indicators = self._build_suspicious_indicators(active_attempts)
        finalize_events = self._attempt_repo.list_recent_finalize_events_global(
            limit=finalize_limit
        )

        exam_map = {exam.id: exam for exam in self._exam_repo.list_exams()}
        exam_summaries: dict[str, dict] = {}
        for attempt in active_attempts:
            exam_id = attempt["exam_id"]
            entry = exam_summaries.setdefault(
                exam_id,
                {
                    "exam_id": exam_id,
                    "exam_name": exam_map.get(exam_id).name if exam_id in exam_map else None,
                    "active_attempt_count": 0,
                    "suspicious_attempt_count": 0,
                },
            )
            entry["active_attempt_count"] += 1

        for item in suspicious_indicators:
            exam_id = item["exam_id"]
            if exam_id not in exam_summaries:
                exam_summaries[exam_id] = {
                    "exam_id": exam_id,
                    "exam_name": exam_map.get(exam_id).name if exam_id in exam_map else None,
                    "active_attempt_count": 0,
                    "suspicious_attempt_count": 0,
                }
            exam_summaries[exam_id]["suspicious_attempt_count"] += 1

        return {
            "as_of": now.isoformat(),
            "active_attempt_count": len(active_attempts),
            "suspicious_attempt_count": len(suspicious_indicators),
            "active_attempts": active_attempts,
            "suspicious_indicators": suspicious_indicators,
            "recent_finalize_events": finalize_events,
            "exam_summaries": sorted(
                exam_summaries.values(), key=lambda item: item["exam_id"]
            ),
        }

    def get_event_stream(
        self,
        limit: int = 100,
        cursor: str | None = None,
        since: str | None = None,
        exam_id: str | None = None,
    ) -> dict:
        if limit < 1 or limit > 500:
            raise ProctoringValidationError("limit must be between 1 and 500")
        if cursor and since:
            raise ProctoringValidationError("Use either 'cursor' or 'since', not both")

        cursor_since: str | None = None
        cursor_event_id: str | None = None
        if cursor:
            cursor_since, cursor_event_id = self._decode_cursor(cursor)
        else:
            cursor_since = self._normalize_since(since)

        if exam_id is not None:
            self._assert_exam_exists(exam_id)

        events = self._attempt_repo.list_attempt_events(
            limit=limit,
            since=cursor_since,
            exam_id=exam_id,
            cursor_event_id=cursor_event_id,
        )
        now = self._normalize_dt(self._now_provider())
        next_cursor = (
            cursor
            if not events and cursor
            else (
                self._encode_cursor(
                    created_at=events[-1]["created_at"],
                    event_id=events[-1]["event_id"],
                )
                if events
                else None
            )
        )
        return {
            "exam_id": exam_id,
            "as_of": now.isoformat(),
            "cursor": cursor,
            "since": cursor_since,
            "limit": limit,
            "count": len(events),
            "events": events,
            "next_since": cursor_since if not events else events[-1]["created_at"],
            "next_cursor": next_cursor,
        }

    def _build_active_attempts(self, exam_id: str, now: datetime) -> list[dict]:
        rows = self._attempt_repo.list_active_attempts_by_exam(exam_id)
        return [self._active_attempt_payload(row, now) for row in rows]

    def _active_attempt_payload(self, row: dict, now: datetime) -> dict:
        started_at = row.get("started_at")
        expires_at = row.get("expires_at")
        started_dt = self._parse_iso(started_at)
        expires_dt = self._parse_iso(expires_at)

        elapsed_seconds = None
        if started_dt is not None:
            elapsed_seconds = max(0, int((now - started_dt).total_seconds()))

        remaining_seconds = None
        if expires_dt is not None:
            remaining_seconds = max(0, int((expires_dt - now).total_seconds()))

        answered_count = int(row.get("answered_count") or 0)
        total_questions = int(row.get("total_questions") or 0)
        progress_percent = (
            (answered_count / total_questions) * 100.0 if total_questions > 0 else 0.0
        )

        return {
            "attempt_id": row["attempt_id"],
            "student_id": row["student_id"],
            "exam_id": row["exam_id"],
            "started_at": started_at,
            "expires_at": expires_at,
            "remaining_seconds": remaining_seconds,
            "elapsed_seconds": elapsed_seconds,
            "answered_question_count": answered_count,
            "total_question_count": total_questions,
            "progress_percent": progress_percent,
        }

    def _build_suspicious_indicators(self, active_attempts: list[dict]) -> list[dict]:
        indicators: list[dict] = []
        for attempt in active_attempts:
            flags: list[str] = []

            remaining = attempt["remaining_seconds"]
            elapsed = attempt["elapsed_seconds"]
            answered = attempt["answered_question_count"]
            total_questions = attempt["total_question_count"]

            if remaining == 0:
                flags.append("timer_elapsed_but_active")
            if remaining is not None and remaining <= 60 and answered == 0:
                flags.append("no_answers_near_timeout")
            if elapsed is not None and elapsed >= 300 and answered == 0:
                flags.append("inactive_for_5_minutes")
            if elapsed is not None and elapsed <= 120 and total_questions >= 8:
                if answered >= max(1, int(total_questions * 0.8)):
                    flags.append("rapid_progression")

            if flags:
                indicators.append(
                    {
                        "attempt_id": attempt["attempt_id"],
                        "student_id": attempt["student_id"],
                        "exam_id": attempt["exam_id"],
                        "flags": flags,
                    }
                )
        return indicators

    def _assert_exam_exists(self, exam_id: str) -> None:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")

    def _normalize_since(self, since: str | None) -> str | None:
        if since is None:
            return None
        value = since.strip()
        if not value:
            return None
        parsed = self._parse_iso(value)
        if parsed is None:
            raise ProctoringValidationError("Invalid 'since' timestamp")
        return parsed.isoformat()

    def _decode_cursor(self, cursor: str) -> tuple[str, str]:
        raw = cursor.strip()
        if not raw:
            raise ProctoringValidationError("Invalid cursor token")
        try:
            padded = raw + ("=" * (-len(raw) % 4))
            decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
            payload = json.loads(decoded)
        except Exception as exc:
            raise ProctoringValidationError("Invalid cursor token") from exc

        created_at = payload.get("created_at")
        event_id = payload.get("event_id")
        if not isinstance(created_at, str) or not isinstance(event_id, str):
            raise ProctoringValidationError("Invalid cursor token")
        if not event_id.strip():
            raise ProctoringValidationError("Invalid cursor token")

        normalized_created_at = self._normalize_since(created_at)
        if normalized_created_at is None:
            raise ProctoringValidationError("Invalid cursor token")
        return normalized_created_at, event_id

    @staticmethod
    def _encode_cursor(created_at: str, event_id: str) -> str:
        payload = json.dumps(
            {"created_at": created_at, "event_id": event_id},
            separators=(",", ":"),
        )
        token = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")
        return token.rstrip("=")

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
    def _normalize_dt(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
