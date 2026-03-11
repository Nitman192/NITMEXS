import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
from phase1_server.models import AttemptStatus
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import DeliveryService
from phase1_server.services.exam_service import ExamCreatePayload, ExamService
from phase1_server.services.question_service import QuestionCreatePayload, QuestionService
from phase1_server.uow import UnitOfWork

try:
    from fastapi.testclient import TestClient
    from phase1_server.app import create_app

    FASTAPI_AVAILABLE = True
except Exception:
    TestClient = None
    create_app = None
    FASTAPI_AVAILABLE = False


class AdminForceSubmitTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "admin_force_submit.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _seed_exam(self) -> str:
        with UnitOfWork(self.db) as uow:
            question = QuestionService(uow.questions).create_question(
                QuestionCreatePayload(
                    text="Force submit question",
                    topic="ops",
                    difficulty="easy",
                    marks=1,
                    options=[("A", True), ("B", False)],
                )
            )
            exam_service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
            exam = exam_service.create_exam(
                ExamCreatePayload(name="Force Submit Exam", duration_minutes=30, negative_marking=0.0)
            )
            exam_service.add_questions(exam.id, [question.id])
            exam_service.publish_exam(exam.id)
            return exam.id

    def _start_attempt(self, exam_id: str, student_id: str) -> str:
        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            started = delivery.start_attempt(exam_id, student_id)
            return started["attempt_id"]

    def test_service_force_submit_attempt(self):
        exam_id = self._seed_exam()
        attempt_id = self._start_attempt(exam_id, "force-student")

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            result = delivery.force_finalize_attempt_by_admin(
                attempt_id=attempt_id,
                actor_id="ops-admin",
                reason="manual_force_submit",
            )
            summary = uow.attempts.get_attempt_result(attempt_id)

        self.assertTrue(result["forced"])
        self.assertEqual(result["status"], "finalized")
        self.assertIsNotNone(summary)

    def test_service_force_submit_expired_attempts(self):
        exam_id = self._seed_exam()
        attempt_a = self._start_attempt(exam_id, "expired-1")
        attempt_b = self._start_attempt(exam_id, "expired-2")

        expired_ts = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        with UnitOfWork(self.db) as uow:
            uow.conn.execute(
                "UPDATE attempts SET expires_at = ? WHERE id IN (?, ?)",
                (expired_ts, attempt_a, attempt_b),
            )

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            report = delivery.force_finalize_expired_attempts(
                actor_id="ops-admin",
                exam_id=exam_id,
                limit=50,
            )

        self.assertEqual(report["processed_count"], 2)
        self.assertEqual(report["finalized_count"], 2)
        self.assertEqual(report["failed_count"], 0)

    def test_service_pause_and_resume_exam_attempts(self):
        exam_id = self._seed_exam()
        attempt_a = self._start_attempt(exam_id, "pause-1")
        attempt_b = self._start_attempt(exam_id, "pause-2")

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            paused = delivery.pause_exam_attempts(
                exam_id=exam_id,
                actor_id="ops-admin",
                reason="network_interruption",
                limit=100,
            )
            attempt_a_after_pause = uow.attempts.get(attempt_a)
            attempt_b_after_pause = uow.attempts.get(attempt_b)
            resumed = delivery.resume_exam_attempts(
                exam_id=exam_id,
                actor_id="ops-admin",
                reason="network_restored",
                limit=100,
            )
            attempt_a_after_resume = uow.attempts.get(attempt_a)
            attempt_b_after_resume = uow.attempts.get(attempt_b)

        self.assertEqual(paused["paused_count"], 2)
        self.assertEqual(attempt_a_after_pause.status, AttemptStatus.PAUSED)
        self.assertEqual(attempt_b_after_pause.status, AttemptStatus.PAUSED)
        self.assertEqual(resumed["resumed_count"], 2)
        self.assertEqual(attempt_a_after_resume.status, AttemptStatus.ACTIVE)
        self.assertEqual(attempt_b_after_resume.status, AttemptStatus.ACTIVE)

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
    def test_admin_force_submit_endpoints(self):
        exam_id = self._seed_exam()
        attempt_id = self._start_attempt(exam_id, "api-force-student")
        expired_attempt = self._start_attempt(exam_id, "api-expired-student")

        expired_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        with UnitOfWork(self.db) as uow:
            uow.conn.execute(
                "UPDATE attempts SET expires_at = ? WHERE id = ?",
                (expired_ts, expired_attempt),
            )

        app = create_app(db_path=self.db_path)
        with TestClient(app) as client:
            headers = {"x-admin": "true", "x-admin-id": "api-admin"}
            force_one = client.post(
                f"/admin/attempts/{attempt_id}/force-submit",
                headers=headers,
                json={"reason": "api_manual"},
            )
            force_expired = client.post(
                f"/admin/attempts/force-submit-expired?exam_id={exam_id}&limit=100",
                headers=headers,
            )

        self.assertEqual(force_one.status_code, 200)
        self.assertEqual(force_expired.status_code, 200)
        self.assertEqual(force_one.json()["data"]["status"], "finalized")
        self.assertGreaterEqual(force_expired.json()["data"]["finalized_count"], 1)

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
    def test_admin_pause_resume_broadcast_and_audit_endpoints(self):
        exam_id = self._seed_exam()
        self._start_attempt(exam_id, "pause-api-1")
        self._start_attempt(exam_id, "pause-api-2")

        app = create_app(db_path=self.db_path)
        with TestClient(app) as client:
            headers = {"x-admin": "true", "x-admin-id": "api-admin"}
            pause_resp = client.post(
                f"/admin/exams/{exam_id}/pause?limit=100",
                headers=headers,
                json={"reason": "api_pause"},
            )
            resume_resp = client.post(
                f"/admin/exams/{exam_id}/resume?limit=100",
                headers=headers,
                json={"reason": "api_resume"},
            )
            broadcast_resp = client.post(
                f"/admin/exams/{exam_id}/broadcast",
                headers=headers,
                json={"message": "Please stay calm and continue.", "severity": "warn"},
            )
            audit_resp = client.get(
                (
                    f"/admin/audit/events?entity_type=exam&entity_id={exam_id}"
                    "&event_type=EXAM_BROADCAST&limit=50"
                ),
                headers=headers,
            )

        self.assertEqual(pause_resp.status_code, 200)
        self.assertEqual(resume_resp.status_code, 200)
        self.assertEqual(broadcast_resp.status_code, 200)
        self.assertEqual(audit_resp.status_code, 200)
        self.assertGreaterEqual(pause_resp.json()["data"]["paused_count"], 1)
        self.assertGreaterEqual(resume_resp.json()["data"]["resumed_count"], 1)
        self.assertEqual(broadcast_resp.json()["data"]["severity"], "warn")
        self.assertGreaterEqual(audit_resp.json()["data"]["count"], 1)


if __name__ == "__main__":
    unittest.main()
