"""Maintenance operations for backup/restore durability workflows."""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from phase1_server.repositories.audit_event_repository import SQLiteAuditEventRepository
from phase1_server.schema_version import EXPECTED_SCHEMA_VERSION


class RestoreValidationError(ValueError):
    pass


class MaintenanceService:
    def __init__(self, db_path: str, logger: logging.Logger | None = None):
        self._db_path = db_path
        self._logger = logger or logging.getLogger("phase1_server")

    def backup_database(self) -> Path:
        source = Path(self._db_path)
        backup_dir = source.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = backup_dir / f"exam_server_{timestamp}.db"

        src_conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        dst_conn = sqlite3.connect(str(target))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()

        self._log_audit_event(
            event_type="BACKUP_CREATED",
            payload={"backup_path": str(target)},
        )
        self._logger.info("backup_created", extra={"backup_path": str(target)})
        return target

    def restore_database(self, restore_path: str) -> None:
        source = Path(restore_path)
        if not source.exists():
            raise RestoreValidationError(f"Restore source not found: {restore_path}")

        restore_version = self._read_schema_version(str(source))
        if restore_version != EXPECTED_SCHEMA_VERSION:
            raise RestoreValidationError(
                f"Schema version mismatch: expected {EXPECTED_SCHEMA_VERSION}, got {restore_version}"
            )

        target = Path(self._db_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        temp_target = target.with_suffix(target.suffix + ".restoring")
        shutil.copy2(source, temp_target)
        os.replace(temp_target, target)

        self._log_audit_event(
            event_type="RESTORE_COMPLETED",
            payload={"restore_source": str(source), "db_path": str(target)},
            target_db_path=str(target),
        )
        self._logger.info("restore_completed", extra={"restore_source": str(source)})

    def _read_schema_version(self, db_path: str) -> int | None:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
            ).fetchone()
            return None if row is None else int(row["version"])
        except sqlite3.Error:
            return None
        finally:
            conn.close()

    def _log_audit_event(
        self,
        event_type: str,
        payload: dict,
        target_db_path: str | None = None,
    ) -> None:
        db_path = target_db_path or self._db_path
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            repo = SQLiteAuditEventRepository(conn)
            repo.log_event(
                entity_type="system",
                entity_id="database",
                actor_type="system",
                actor_id="maintenance",
                event_type=event_type,
                payload=payload,
                created_at=datetime.now(timezone.utc).isoformat(),
                version=None,
            )
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            self._logger.exception("audit_event_log_failed")
        finally:
            conn.close()
