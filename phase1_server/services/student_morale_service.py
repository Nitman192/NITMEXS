"""Lightweight offline morale coach for student attempts."""

from __future__ import annotations

from datetime import datetime, timezone


class StudentMoraleService:
    def build_message(self, attempt_status: dict) -> dict:
        total_questions = max(1, int(attempt_status.get("total_question_count") or 0))
        answered_questions = int(attempt_status.get("answered_question_count") or 0)
        progress_percent = round((answered_questions / total_questions) * 100.0, 1)
        remaining_minutes = self._remaining_minutes(attempt_status.get("expires_at"))

        if progress_percent < 25:
            title = "Strong Start"
            message = "Calm raho, pehle easy questions secure karo."
            focus_tip = "First pass me sirf sure answers mark karo, doubtful ko review pe chhodo."
        elif progress_percent < 60:
            title = "Great Momentum"
            message = "Aap rhythm me ho, isi pace ko maintain rakho."
            focus_tip = "Har 5 questions ke baad timer check karo aur pace adjust karo."
        elif progress_percent < 90:
            title = "Almost There"
            message = "Bahut achha progress, ab accuracy pe focus karo."
            focus_tip = "Review list ke questions me elimination method use karo."
        else:
            title = "Finish Strong"
            message = "Final stretch hai, confidence ke saath complete karo."
            focus_tip = "Submit se pehle unanswered palette slots quickly verify karo."

        if remaining_minutes <= 10:
            message = "Final time window hai, high-confidence decisions lo."
            focus_tip = "Timer low hai: sirf high-probability answers pe focus karo."

        return {
            "title": title,
            "message": message,
            "focus_tip": focus_tip,
            "progress_percent": progress_percent,
            "remaining_minutes": remaining_minutes,
        }

    @staticmethod
    def _remaining_minutes(expires_at_iso: str | None) -> int:
        if not expires_at_iso:
            return 0
        try:
            expires_at = datetime.fromisoformat(expires_at_iso)
        except ValueError:
            return 0
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        remaining_seconds = max(
            0,
            int((expires_at - datetime.now(timezone.utc)).total_seconds()),
        )
        return remaining_seconds // 60

