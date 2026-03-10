import tempfile
import unittest
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.audit_service import AuditService
from phase1_server.services.exam_service import ExamService
from phase1_server.services.question_import_service import (
    CsvImportError,
    ExamQuestionPackageCsvImportService,
    QuestionCsvImportService,
)
from phase1_server.services.question_service import QuestionService
from phase1_server.uow import UnitOfWork

try:
    from fastapi.testclient import TestClient
    from phase1_server.app import create_app

    FASTAPI_AVAILABLE = True
except Exception:
    TestClient = None
    create_app = None
    FASTAPI_AVAILABLE = False


class QuestionCsvImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "question_import.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _import(self, csv_content: str):
        with UnitOfWork(self.db) as uow:
            service = QuestionService(uow.questions)
            importer = QuestionCsvImportService(service)
            return importer.import_csv(csv_content)

    def _import_exam_package(self, csv_content: str):
        with UnitOfWork(self.db) as uow:
            question_service = QuestionService(uow.questions)
            exam_service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
            importer = ExamQuestionPackageCsvImportService(question_service, exam_service)
            return importer.import_csv(csv_content)

    def test_valid_csv(self):
        csv_content = (
            "text,topic,difficulty,marks,"
            "option1,option1_is_correct,"
            "option2,option2_is_correct,"
            "option3,option3_is_correct,"
            "option4,option4_is_correct\n"
            "What is 2+2?,math,easy,1,3,false,4,true,5,false,6,false\n"
        )

        result = self._import(csv_content)

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.inserted, 1)
        self.assertEqual(result.failed, 0)

    def test_invalid_rows(self):
        csv_content = (
            "text,topic,difficulty,marks,"
            "option1,option1_is_correct,"
            "option2,option2_is_correct,"
            "option3,option3_is_correct,"
            "option4,option4_is_correct\n"
            "Bad question,math,easy,abc,3,false,4,true,,,\n"
            "Another question,math,easy,2,3,true,4,true,,,\n"
        )

        result = self._import(csv_content)

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.inserted, 0)
        self.assertEqual(result.failed, 2)
        self.assertEqual(result.errors[0].row, 2)
        self.assertIn("marks must be integer", result.errors[0].error)

    def test_partial_success(self):
        csv_content = (
            "text,topic,difficulty,marks,"
            "option1,option1_is_correct,"
            "option2,option2_is_correct,"
            "option3,option3_is_correct,"
            "option4,option4_is_correct\n"
            "Valid question,math,easy,2,3,false,4,true,5,false,6,false\n"
            "Invalid question,math,easy,2,3,true,4,true,,,\n"
        )

        result = self._import(csv_content)

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.inserted, 1)
        self.assertEqual(result.failed, 1)

    def test_empty_file(self):
        with self.assertRaises(CsvImportError):
            self._import("")

    def test_exam_package_import_creates_exam_and_questions(self):
        csv_content = (
            "exam_name,duration_minutes,negative_marking,publish_exam,"
            "text,topic,difficulty,marks,"
            "option1,option1_is_correct,"
            "option2,option2_is_correct,"
            "option3,option3_is_correct,"
            "option4,option4_is_correct\n"
            "LAN Mock,30,0.25,true,What is 1+1?,math,easy,1,2,true,1,false,3,false,4,false\n"
            "LAN Mock,30,0.25,true,OSI layers?,networking,medium,2,7,true,6,false,5,false,4,false\n"
        )

        result = self._import_exam_package(csv_content)

        self.assertEqual(result.exam_name, "LAN Mock")
        self.assertEqual(result.inserted, 2)
        self.assertEqual(result.failed, 0)
        self.assertTrue(result.published)
        self.assertEqual(len(result.question_ids), 2)

        with UnitOfWork(self.db) as uow:
            question_ids = uow.exams.list_question_ids(result.exam_id)
        self.assertEqual(len(question_ids), 2)

    def test_exam_package_import_flags_mixed_exam_name_rows(self):
        csv_content = (
            "exam_name,duration_minutes,negative_marking,publish_exam,"
            "text,topic,difficulty,marks,"
            "option1,option1_is_correct,"
            "option2,option2_is_correct,"
            "option3,option3_is_correct,"
            "option4,option4_is_correct\n"
            "Exam One,30,0.0,false,What is 1+1?,math,easy,1,2,true,1,false,3,false,4,false\n"
            "Exam Two,30,0.0,false,What is 2+2?,math,easy,1,4,true,2,false,3,false,1,false\n"
        )

        result = self._import_exam_package(csv_content)

        self.assertEqual(result.inserted, 1)
        self.assertEqual(result.failed, 1)
        self.assertIn("must match first row", result.errors[0].error)

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
    def test_admin_exam_package_csv_endpoint(self):
        csv_content = (
            "exam_name,duration_minutes,negative_marking,publish_exam,"
            "text,topic,difficulty,marks,"
            "option1,option1_is_correct,"
            "option2,option2_is_correct,"
            "option3,option3_is_correct,"
            "option4,option4_is_correct\n"
            "Endpoint Exam,40,0.5,false,Question A,topic,easy,1,opt1,true,opt2,false,opt3,false,opt4,false\n"
        )

        app = create_app(db_path=self.db_path)
        with TestClient(app) as client:
            response = client.post(
                "/admin/exams/import-question-pack-csv",
                headers={"x-admin": "true"},
                files={"file": ("exam_pack.csv", csv_content, "text/csv")},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["exam_name"], "Endpoint Exam")
        self.assertEqual(payload["inserted"], 1)
        self.assertIn("exam_id", payload)


if __name__ == "__main__":
    unittest.main()
