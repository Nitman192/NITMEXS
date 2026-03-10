import sqlite3
import tempfile
import unittest
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
from phase1_server.schema_version import EXPECTED_SCHEMA_VERSION
from phase1_server.services.maintenance_service import (
    MaintenanceService,
    RestoreValidationError,
)


class DurabilityMaintenanceTests(unittest.TestCase):
    def test_schema_version_validation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "schema_validation.db")
            db = Database(SQLiteConfig(db_path=db_path))
            db.initialize()
            db.ensure_expected_schema_version(EXPECTED_SCHEMA_VERSION)
            with self.assertRaises(RuntimeError):
                db.ensure_expected_schema_version(EXPECTED_SCHEMA_VERSION + 1)

    def test_backup_file_creation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "exam.db")
            db = Database(SQLiteConfig(db_path=db_path))
            db.initialize()

            service = MaintenanceService(db_path)
            backup_path = service.backup_database()

            self.assertTrue(backup_path.exists())
            self.assertIn("backups", str(backup_path.parent))

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute(
                    "SELECT event_type FROM audit_events WHERE event_type = 'BACKUP_CREATED' LIMIT 1"
                ).fetchone()
            finally:
                conn.close()
            self.assertIsNotNone(row)

    def test_restore_validation_failure_on_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target_db = str(Path(tmp_dir) / "target.db")
            restore_db = str(Path(tmp_dir) / "restore.db")

            target = Database(SQLiteConfig(db_path=target_db))
            target.initialize()

            restore = Database(SQLiteConfig(db_path=restore_db))
            restore.initialize()

            conn = sqlite3.connect(restore_db)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES(?, datetime('now'))",
                    (EXPECTED_SCHEMA_VERSION + 10,),
                )
                conn.commit()
            finally:
                conn.close()

            service = MaintenanceService(target_db)
            with self.assertRaises(RestoreValidationError):
                service.restore_database(restore_db)


if __name__ == "__main__":
    unittest.main()
