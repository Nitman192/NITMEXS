import tempfile
import unittest
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import DeliveryService
from phase1_server.services.exam_service import ExamCreatePayload, ExamService
from phase1_server.services.question_service import QuestionCreatePayload, QuestionService
from phase1_server.services.student_morale_service import StudentMoraleService
from phase1_server.services.student_registry_service import (
    StudentGeneratePayload,
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


class StudentRegistryAndMoraleTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "student_registry_morale.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _seed_attempt(self) -> tuple[str, str]:
        with UnitOfWork(self.db) as uow:
            question_service = QuestionService(uow.questions)
            question = question_service.create_question(
                QuestionCreatePayload(
                    text="What is 2 + 2?",
                    topic="math",
                    difficulty="easy",
                    marks=1,
                    options=[("4", True), ("3", False), ("5", False), ("2", False)],
                )
            )
            exam_service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
            exam = exam_service.create_exam(
                ExamCreatePayload(name="Morale Exam", duration_minutes=30, negative_marking=0.0)
            )
            exam_service.add_questions(exam.id, [question.id])
            exam_service.publish_exam(exam.id)

            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
            )
            started = delivery.start_attempt(exam.id, "cadet-01")
            return started["attempt_id"], "cadet-01"

    def test_student_registry_service_register_and_generate(self):
        with UnitOfWork(self.db) as uow:
            service = StudentRegistryService(uow.student_accounts)
            created = service.register_student(
                StudentRegisterPayload(
                    student_id="cadet-01",
                    display_name="Cadet One",
                    created_by="admin-1",
                )
            )
            generated = service.generate_students(
                StudentGeneratePayload(prefix="cadet", count=3, created_by="admin-1")
            )
            listed = service.list_students(limit=20)

        self.assertEqual(created["student_id"], "cadet-01")
        self.assertEqual(generated["generated_count"], 3)
        self.assertGreaterEqual(len(listed), 4)

    def test_morale_service_response_shape(self):
        service = StudentMoraleService()
        message = service.build_message(
            {
                "total_question_count": 20,
                "answered_question_count": 7,
                "expires_at": None,
            }
        )
        self.assertIn("title", message)
        self.assertIn("message", message)
        self.assertIn("focus_tip", message)
        self.assertIn("progress_percent", message)

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
    def test_admin_student_registry_endpoints(self):
        app = create_app(db_path=self.db_path)
        with TestClient(app) as client:
            create_resp = client.post(
                "/admin/students/register",
                headers={"x-admin": "true", "x-admin-id": "admin-2"},
                json={"student_id": "cadet-99", "display_name": "Cadet Ninety Nine"},
            )
            generate_resp = client.post(
                "/admin/students/generate",
                headers={"x-admin": "true", "x-admin-id": "admin-2"},
                json={"prefix": "cadet", "count": 2},
            )
            list_resp = client.get(
                "/admin/students",
                headers={"x-admin": "true"},
            )

        self.assertEqual(create_resp.status_code, 201)
        self.assertEqual(create_resp.json()["data"]["student_id"], "cadet-99")
        self.assertEqual(generate_resp.status_code, 200)
        self.assertEqual(generate_resp.json()["data"]["generated_count"], 2)
        self.assertEqual(list_resp.status_code, 200)
        self.assertGreaterEqual(list_resp.json()["data"]["count"], 3)

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
    def test_student_morale_endpoint(self):
        attempt_id, student_id = self._seed_attempt()
        app = create_app(db_path=self.db_path)
        with TestClient(app) as client:
            response = client.get(
                f"/student/attempts/{attempt_id}/morale",
                headers={"x-student-id": student_id},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["attempt_id"], attempt_id)
        self.assertIn("title", payload)
        self.assertIn("message", payload)
        self.assertIn("focus_tip", payload)


if __name__ == "__main__":
    unittest.main()

