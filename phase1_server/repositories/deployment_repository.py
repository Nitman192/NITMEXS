"""Repository for singleton deployment profile settings."""

from __future__ import annotations

import sqlite3
from typing import Protocol

from phase1_server.models import DeploymentSettings


class DeploymentSettingsRepository(Protocol):
    def get(self) -> DeploymentSettings | None: ...

    def set_trusted_host_fingerprint(self, fingerprint: str, updated_at: str) -> None: ...


class SQLiteDeploymentSettingsRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get(self) -> DeploymentSettings | None:
        row = self._conn.execute(
            """
            SELECT id, deployment_profile, branding_profile, student_result_policy,
                   trusted_host_fingerprint, created_at, updated_at
            FROM deployment_settings
            WHERE id = 1
            """
        ).fetchone()
        if row is None:
            return None
        return DeploymentSettings(
            id=int(row["id"]),
            deployment_profile=row["deployment_profile"],
            branding_profile=row["branding_profile"],
            student_result_policy=row["student_result_policy"],
            trusted_host_fingerprint=row["trusted_host_fingerprint"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def set_trusted_host_fingerprint(self, fingerprint: str, updated_at: str) -> None:
        self._conn.execute(
            """
            UPDATE deployment_settings
            SET trusted_host_fingerprint = ?, updated_at = ?
            WHERE id = 1
            """,
            (fingerprint, updated_at),
        )
