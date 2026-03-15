"""Repository for generated result/export artifact metadata."""

from __future__ import annotations

import sqlite3
from typing import Protocol

from phase1_server.models import ResultArtifact


class ResultArtifactRepository(Protocol):
    def create(self, artifact: ResultArtifact) -> None: ...

    def list_recent(
        self,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 50,
    ) -> list[ResultArtifact]: ...


class SQLiteResultArtifactRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(self, artifact: ResultArtifact) -> None:
        self._conn.execute(
            """
            INSERT INTO result_artifacts(
                id, artifact_type, entity_type, entity_id, created_by,
                file_name, content_type, checksum, reference_code, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact.id,
                artifact.artifact_type,
                artifact.entity_type,
                artifact.entity_id,
                artifact.created_by,
                artifact.file_name,
                artifact.content_type,
                artifact.checksum,
                artifact.reference_code,
                artifact.created_at,
            ),
        )

    def list_recent(
        self,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 50,
    ) -> list[ResultArtifact]:
        rows = self._conn.execute(
            """
            SELECT
                id, artifact_type, entity_type, entity_id, created_by,
                file_name, content_type, checksum, reference_code, created_at
            FROM result_artifacts
            WHERE (? IS NULL OR entity_type = ?)
              AND (? IS NULL OR entity_id = ?)
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (entity_type, entity_type, entity_id, entity_id, limit),
        ).fetchall()
        return [
            ResultArtifact(
                id=row["id"],
                artifact_type=row["artifact_type"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                created_by=row["created_by"],
                file_name=row["file_name"],
                content_type=row["content_type"],
                checksum=row["checksum"],
                reference_code=row["reference_code"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
