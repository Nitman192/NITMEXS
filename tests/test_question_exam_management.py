import tempfile
import unittest
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
from phase1_server.models import ExamStatus
from phase1_server.services.exam_service import (
    ExamAlreadyPublishedError,
    ExamCreatePayload,
    ExamService,
    ExamValidationError,
)
from phase1_server.services.question_service import QuestionCreatePayload, QuestionService
from phase1_server.uow import UnitOfWork


class QuestionExamManagementTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "question_exam.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _create_question(self, uow, text: str = "What is 2+2?") -> str:
        service = QuestionService(uow.questions)
        question = service.create_question(
            QuestionCreatePayload(
                text=text,
                topic="math",
                difficulty="easy",
                marks=1.0,
                options=[("3", False), ("4", True), ("5", False)],
            )
        )
        return question.id

    def test_question_creation(self):
        with UnitOfWork(self.db) as uow:
            question_id = self._create_question(uow)
            items = QuestionService(uow.questions).list_questions()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], question_id)
        self.assertEqual(len(items[0]["options"]), 3)

    def test_exam_creation(self):
        with UnitOfWork(self.db) as uow:
            service = ExamService(uow.exams, uow.questions)
            exam = service.create_exam(
                ExamCreatePayload(
                    name="Midterm",
                    duration_minutes=60,
                    negative_marking=0.25,
                )
            )

        self.assertEqual(exam.name, "Midterm")
        self.assertFalse(exam.published)

    def test_publishing_rules(self):
        with UnitOfWork(self.db) as uow:
            question_id = self._create_question(uow)
            service = ExamService(uow.exams, uow.questions)
            exam = service.create_exam(
                ExamCreatePayload(
                    name="Final",
                    duration_minutes=90,
                    negative_marking=0.25,
                )
            )
            service.add_questions(exam.id, [question_id])
            published = service.publish_exam(exam.id)
            self.assertTrue(published.published)
            with self.assertRaises(ExamAlreadyPublishedError):
                service.publish_exam(exam.id)

    def test_snapshot_generation(self):
        with UnitOfWork(self.db) as uow:
            question_ids = [self._create_question(uow, text=f"Question {idx}") for idx in range(5)]
            service = ExamService(uow.exams, uow.questions)
            exam = service.create_exam(
                ExamCreatePayload(
                    name="Snapshot Test",
                    duration_minutes=45,
                    negative_marking=0,
                )
            )
            service.add_questions(exam.id, question_ids)
            snapshot = service.generate_exam_snapshot(exam.id, attempt_id="attempt-1")

        self.assertEqual(len(snapshot), 5)
        self.assertEqual(
            sorted(item["question_id"] for item in snapshot),
            sorted(question_ids),
        )
        self.assertEqual([item["order_index"] for item in snapshot], [1, 2, 3, 4, 5])

    def test_repository_isolation_per_unit_of_work(self):
        with UnitOfWork(self.db) as uow1:
            question_id = self._create_question(uow1)
            self.assertTrue(uow1.questions.question_exists(question_id))

        with UnitOfWork(self.db) as uow2:
            self.assertTrue(uow2.questions.question_exists(question_id))


    def test_exam_close_changes_state_and_logs_event(self):
        with UnitOfWork(self.db) as uow:
            question_id = self._create_question(uow)
            service = ExamService(uow.exams, uow.questions)
            exam = service.create_exam(
                ExamCreatePayload(
                    name="Close Me",
                    duration_minutes=60,
                    negative_marking=0,
                )
            )
            service.add_questions(exam.id, [question_id])
            service.publish_exam(exam.id)
            closed = service.close_exam(exam.id, actor_id="admin1")

            events = uow.conn.execute(
                "SELECT event_type FROM exam_audit_logs WHERE exam_id = ?",
                (exam.id,),
            ).fetchall()

        self.assertEqual(closed.status, ExamStatus.CLOSED)
        self.assertFalse(closed.published)
        self.assertIn("EXAM_CLOSED", [row["event_type"] for row in events])

    def test_cannot_publish_closed_exam(self):
        with UnitOfWork(self.db) as uow:
            question_id = self._create_question(uow)
            service = ExamService(uow.exams, uow.questions)
            exam = service.create_exam(
                ExamCreatePayload(
                    name="Closed Publish",
                    duration_minutes=60,
                    negative_marking=0,
                )
            )
            service.add_questions(exam.id, [question_id])
            service.publish_exam(exam.id)
            service.close_exam(exam.id, actor_id="admin1")

            with self.assertRaises(ExamValidationError):
                service.publish_exam(exam.id)


if __name__ == "__main__":
    unittest.main()
