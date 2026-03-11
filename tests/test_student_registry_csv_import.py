import tempfile
import unittest
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.student_registry_csv_service import (
    StudentRegistryCsvService,
)
from phase1_server.services.student_registry_service import (
    StudentRegisterPayload,
    StudentRegistryService,
)
from phase1_server.uow import UnitOfWork

try:
    from fastapi.testclient import TestClient
    from phase1_server.app import create_app

    FASTAPI_AVAILABLE = True
except Exception:
    TestClient = None
    create_app = None
    FASTAPI_AVAILABLE = False


class StudentRegistryCsvImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "student_registry_csv.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_service_import_csv_reports_partial_success(self):
        csv_content = (
            "student_id,display_name,created_by\n"
            "cadet-001,Cadet One,ops-admin\n"
            "cadet-001,Duplicate Cadet,ops-admin\n"
            "x,Too Short,ops-admin\n"
            "cadet-002,Cadet Two,\n"
        )

        with UnitOfWork(self.db) as uow:
            registry_service = StudentRegistryService(uow.student_accounts)
            csv_service = StudentRegistryCsvService(registry_service)
            result = csv_service.import_csv(csv_content, default_created_by="fallback-admin")
            students = registry_service.list_students(limit=20)

        self.assertEqual(result.total_rows, 4)
        self.assertEqual(result.inserted, 2)
        self.assertEqual(result.failed, 2)
        self.assertEqual(len(students), 2)
        self.assertTrue(any("already exists" in item.error for item in result.errors))
        self.assertTrue(any("student_id must be" in item.error for item in result.errors))

    def test_service_export_csv_includes_registered_students(self):
        with UnitOfWork(self.db) as uow:
            registry_service = StudentRegistryService(uow.student_accounts)
            registry_service.register_student(
                StudentRegisterPayload(
                    student_id="cadet-010",
                    display_name="Cadet Ten",
                    created_by="admin-csv",
                )
            )
            csv_service = StudentRegistryCsvService(registry_service)
            exported = csv_service.export_csv(limit=50)

        self.assertIn("student_id,display_name,status,created_by,created_at", exported)
        self.assertIn("cadet-010,Cadet Ten,ACTIVE,admin-csv", exported)

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
    def test_admin_student_csv_endpoints(self):
        app = create_app(db_path=self.db_path)
        csv_content = (
            "student_id,display_name\n"
            "cadet-101,Cadet One Zero One\n"
            "cadet-102,Cadet One Zero Two\n"
        )

        with TestClient(app) as client:
            import_response = client.post(
                "/admin/students/import-csv",
                headers={"x-admin": "true", "x-admin-id": "csv-admin"},
                files={"file": ("students.csv", csv_content, "text/csv")},
            )
            export_response = client.get(
                "/admin/students/export-csv?limit=200",
                headers={"x-admin": "true"},
            )

        self.assertEqual(import_response.status_code, 200)
        payload = import_response.json()["data"]
        self.assertEqual(payload["inserted"], 2)
        self.assertEqual(payload["failed"], 0)

        self.assertEqual(export_response.status_code, 200)
        self.assertIn("text/csv", export_response.headers.get("content-type", ""))
        self.assertIn("cadet-101", export_response.text)
        self.assertIn("cadet-102", export_response.text)


if __name__ == "__main__":
    unittest.main()
