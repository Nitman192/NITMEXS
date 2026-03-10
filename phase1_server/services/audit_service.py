"""Service for immutable audit event logging and timeline retrieval."""

from __future__ import annotations

from typing import Any

from phase1_server.models import utc_now_iso
from phase1_server.repositories.audit_event_repository import AuditEventRepository


class AuditService:
    def __init__(self, audit_repo: AuditEventRepository):
        self._audit_repo = audit_repo

    def log_event(
        self,
        entity_type: str,
        entity_id: str,
        actor_type: str,
        actor_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        created_at: str | None = None,
        version: int | None = None,
    ) -> None:
        self._audit_repo.log_event(
            entity_type=entity_type,
            entity_id=entity_id,
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=event_type,
            payload=payload,
            created_at=created_at or utc_now_iso(),
            version=version,
        )

    def list_entity_timeline(self, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
        return self._audit_repo.list_events(entity_type=entity_type, entity_id=entity_id)
