import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
    from phase1_server.app import create_app
    FASTAPI_AVAILABLE = True
except Exception:
    TestClient = None
    create_app = None
    FASTAPI_AVAILABLE = False

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import (
    AnswerSubmissionPayload,
    DeliveryService,
)
from phase1_server.services.exam_service import ExamCreatePayload, ExamService
from phase1_server.services.question_service import QuestionCreatePayload, QuestionService
from phase1_server.uow import UnitOfWork


class AuditEventsTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "audit_events.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _seed_exam(self) -> str:
        with UnitOfWork(self.db) as uow:
            question_service = QuestionService(uow.questions)
            exam_service = ExamService(
                uow.exams,
                uow.questions,
                AuditService(uow.audit_events),
            )
            q = question_service.create_question(
                QuestionCreatePayload(
                    text="Q1",
                    topic="topic",
                    difficulty="easy",
                    marks=2,
                    options=[("A", True), ("B", False)],
                )
            )
            exam = exam_service.create_exam(
                ExamCreatePayload(
                    name="Audit Exam",
                    duration_minutes=30,
                    negative_marking=0,
                )
            )
            exam_service.add_questions(exam.id, [q.id])
            exam_service.publish_exam(exam.id)
            return exam.id

    def test_event_logged_on_answer_submit(self):
        exam_id = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
            )
            start = service.start_attempt(exam_id, "s1")
            first = start["first_question"]
            service.submit_answer(
                AnswerSubmissionPayload(
                    attempt_id=start["attempt_id"],
                    question_id=first["question"]["id"],
                    selected_option_id=first["options"][0]["id"],
                ),
                student_id="s1",
            )
            events = AuditService(uow.audit_events).list_entity_timeline(
                entity_type="attempt",
                entity_id=start["attempt_id"],
            )

        event_types = [event["event_type"] for event in events]
        self.assertIn("ANSWER_SUBMITTED", event_types)

    def test_event_logged_on_finalize(self):
        exam_id = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
            )
            start = service.start_attempt(exam_id, "s2")
            service.finalize_attempt(start["attempt_id"], "s2")
            events = AuditService(uow.audit_events).list_entity_timeline(
                entity_type="attempt",
                entity_id=start["attempt_id"],
            )

        event_types = [event["event_type"] for event in events]
        self.assertIn("FINALIZED", event_types)
        self.assertIn("GRADED", event_types)

    def test_timeline_returns_ordered_events(self):
        exam_id = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
            )
            start = service.start_attempt(exam_id, "s3")
            first = start["first_question"]
            service.submit_answer(
                AnswerSubmissionPayload(
                    attempt_id=start["attempt_id"],
                    question_id=first["question"]["id"],
                    selected_option_id=first["options"][0]["id"],
                ),
                student_id="s3",
            )
            service.finalize_attempt(start["attempt_id"], "s3")

            timeline = AuditService(uow.audit_events).list_entity_timeline(
                entity_type="attempt",
                entity_id=start["attempt_id"],
            )

        created_times = [row["created_at"] for row in timeline]
        self.assertEqual(created_times, sorted(created_times))

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
    def test_timeline_unauthorized_access_blocked(self):
        exam_id = self._seed_exam()
        app = create_app(db_path=self.db_path)
        with TestClient(app) as client:
            response = client.get(f"/admin/attempts/{exam_id}/timeline")

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
