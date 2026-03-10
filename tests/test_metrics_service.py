import tempfile
import unittest

from phase1_server.db import Database, SQLiteConfig
from phase1_server.models import Attempt
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import DeliveryService, AttemptStateError
from phase1_server.services.exam_service import ExamCreatePayload, ExamService
from phase1_server.services.metrics_service import MetricsService
from phase1_server.services.question_service import QuestionCreatePayload, QuestionService
from phase1_server.uow import UnitOfWork


class StaleAttemptRepository:
    def __init__(self, base_repo, stale_attempt: Attempt):
        self._base_repo = base_repo
        self._stale_attempt = stale_attempt

    def get(self, attempt_id: str):
        if attempt_id == self._stale_attempt.id:
            return self._stale_attempt
        return self._base_repo.get(attempt_id)

    def __getattr__(self, item):
        return getattr(self._base_repo, item)


class MetricsFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db")
        self.db = Database(SQLiteConfig(db_path=self.tmp.name))
        self.db.initialize()

    def tearDown(self):
        self.tmp.close()

    def _seed_exam(self) -> str:
        with UnitOfWork(self.db) as uow:
            q = QuestionService(uow.questions).create_question(
                QuestionCreatePayload(
                    text="M1",
                    topic="topic",
                    difficulty="easy",
                    marks=1,
                    options=[("A", True), ("B", False)],
                )
            )
            exam_service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
            exam = exam_service.create_exam(
                ExamCreatePayload(name="MExam", duration_minutes=30, negative_marking=0)
            )
            exam_service.add_questions(exam.id, [q.id])
            exam_service.publish_exam(exam.id)
            return exam.id

    def test_metrics_increment_on_finalize_and_conflict(self):
        exam_id = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            metrics = MetricsService(uow.metrics)
            service = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                metrics_service=metrics,
            )
            start = service.start_attempt(exam_id, "mx-1")
            stale = uow.attempts.get(start["attempt_id"])
            self.assertIsNotNone(stale)

            service.finalize_attempt(start["attempt_id"], "mx-1")

            stale_service = DeliveryService(
                StaleAttemptRepository(uow.attempts, stale),
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                metrics_service=metrics,
            )
            with self.assertRaises(AttemptStateError):
                stale_service.finalize_attempt(start["attempt_id"], "mx-1")

            snapshot = metrics.get_metrics()

        finalize_rows = snapshot.get("finalize_to_grade_ms", [])
        conflict_rows = snapshot.get("concurrency_conflict_count", [])
        self.assertTrue(finalize_rows)
        self.assertGreaterEqual(finalize_rows[0]["count"], 1)
        self.assertTrue(conflict_rows)
        self.assertEqual(conflict_rows[0]["count"], 1)


if __name__ == "__main__":
    unittest.main()
