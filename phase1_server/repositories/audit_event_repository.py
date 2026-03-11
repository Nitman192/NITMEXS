"""Repository for immutable audit events."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any, Protocol


class AuditEventRepository(Protocol):
    def log_event(
        self,
        entity_type: str,
        entity_id: str,
        actor_type: str,
        actor_id: str,
        event_type: str,
        payload: dict[str, Any] | None,
        created_at: str,
        version: int | None = None,
    ) -> None: ...

    def list_events(self, entity_type: str, entity_id: str) -> list[dict[str, Any]]: ...

    def search_events(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        event_type: str | None = None,
        actor_type: str | None = None,
        actor_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]: ...


class SQLiteAuditEventRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def log_event(
        self,
        entity_type: str,
        entity_id: str,
        actor_type: str,
        actor_id: str,
        event_type: str,
        payload: dict[str, Any] | None,
        created_at: str,
        version: int | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO audit_events(
                id, entity_type, entity_id, actor_type, actor_id,
                event_type, payload_json, created_at, version
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                entity_type,
                entity_id,
                actor_type,
                actor_id,
                event_type,
                json.dumps(payload or {}, separators=(",", ":")),
                created_at,
                version,
            ),
        )

    def list_events(self, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT id, entity_type, entity_id, actor_type, actor_id,
                   event_type, payload_json, created_at, version
            FROM audit_events
            WHERE entity_type = ? AND entity_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (entity_type, entity_id),
        ).fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except json.JSONDecodeError:
                payload = {}
            result.append(
                {
                    "id": row["id"],
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "actor_type": row["actor_type"],
                    "actor_id": row["actor_id"],
                    "event_type": row["event_type"],
                    "payload": payload,
                    "created_at": row["created_at"],
                    "version": row["version"],
                }
            )
        return result

    def search_events(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        event_type: str | None = None,
        actor_type: str | None = None,
        actor_id: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT id, entity_type, entity_id, actor_type, actor_id,
                   event_type, payload_json, created_at, version
            FROM audit_events
            WHERE
                (? IS NULL OR entity_type = ?)
                AND (? IS NULL OR entity_id = ?)
                AND (? IS NULL OR event_type = ?)
                AND (? IS NULL OR actor_type = ?)
                AND (? IS NULL OR actor_id = ?)
                AND (? IS NULL OR created_at >= ?)
                AND (? IS NULL OR created_at <= ?)
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (
                entity_type,
                entity_type,
                entity_id,
                entity_id,
                event_type,
                event_type,
                actor_type,
                actor_type,
                actor_id,
                actor_id,
                since,
                since,
                until,
                until,
                limit,
            ),
        ).fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except json.JSONDecodeError:
                payload = {}
            result.append(
                {
                    "id": row["id"],
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "actor_type": row["actor_type"],
                    "actor_id": row["actor_id"],
                    "event_type": row["event_type"],
                    "payload": payload,
                    "created_at": row["created_at"],
                    "version": row["version"],
                }
            )
        return result
