"""Minimal attempt state machine service enforcing valid transitions."""

from __future__ import annotations

from dataclasses import dataclass

from phase1_server.models import AttemptStatus, utc_now_iso
from phase1_server.repositories.attempt_repository import AttemptRepository


class AttemptNotFoundError(ValueError):
    pass


class InvalidAttemptTransitionError(ValueError):
    pass


@dataclass(frozen=True)
class TransitionResult:
    attempt_id: str
    from_status: AttemptStatus
    to_status: AttemptStatus
    updated_at: str


class AttemptStateService:
    ALLOWED_TRANSITIONS: dict[AttemptStatus, set[AttemptStatus]] = {
        AttemptStatus.CREATED: {AttemptStatus.ACTIVE, AttemptStatus.ARCHIVED},
        AttemptStatus.ACTIVE: {AttemptStatus.PAUSED, AttemptStatus.FINALIZED},
        AttemptStatus.PAUSED: {AttemptStatus.ACTIVE, AttemptStatus.FINALIZED},
        AttemptStatus.FINALIZED: {AttemptStatus.GRADED, AttemptStatus.ARCHIVED},
        AttemptStatus.GRADED: {AttemptStatus.ARCHIVED},
        AttemptStatus.ARCHIVED: set(),
    }

    def __init__(self, repo: AttemptRepository):
        self._repo = repo

    def transition(self, attempt_id: str, to_status: AttemptStatus) -> TransitionResult:
        attempt = self._repo.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"Attempt '{attempt_id}' not found")

        if to_status == attempt.status:
            return TransitionResult(
                attempt_id=attempt.id,
                from_status=attempt.status,
                to_status=to_status,
                updated_at=attempt.updated_at,
            )

        allowed = self.ALLOWED_TRANSITIONS[attempt.status]
        if to_status not in allowed:
            raise InvalidAttemptTransitionError(
                f"Invalid attempt transition: {attempt.status.value} -> {to_status.value}"
            )

        now = utc_now_iso()
        submitted_at = now if to_status is AttemptStatus.FINALIZED else None
        self._repo.update_status(attempt.id, to_status, now, submitted_at=submitted_at)
        return TransitionResult(
            attempt_id=attempt.id,
            from_status=attempt.status,
            to_status=to_status,
            updated_at=now,
        )
