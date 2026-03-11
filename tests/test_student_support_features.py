import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
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


class StudentSupportFeatureTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "student_support.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _seed_exam(self) -> str:
        with UnitOfWork(self.db) as uow:
            question = QuestionService(uow.questions).create_question(
                QuestionCreatePayload(
                    text="Support feature question",
                    topic="ops",
                    difficulty="easy",
                    marks=2,
                    options=[("A", True), ("B", False), ("C", False)],
                )
            )
            exam_service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
            exam = exam_service.create_exam(
                ExamCreatePayload(name="Support Feature Exam", duration_minutes=20, negative_marking=0.0)
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

    def test_service_reports_issues_and_rules(self):
        exam_id = self._seed_exam()
        attempt_id = self._start_attempt(exam_id, "support-student")

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            question_payload = delivery.fetch_question(attempt_id, 1, "support-student")
            question_id = question_payload["question"]["id"]
            q_issue = delivery.report_question_issue(
                attempt_id=attempt_id,
                question_id=question_id,
                issue_type="typo",
                note="Option text has typo",
                student_id="support-student",
            )
            tech_issue = delivery.report_technical_issue(
                attempt_id=attempt_id,
                issue_type="network",
                note="Temporary lag observed",
                student_id="support-student",
            )
            rules = delivery.get_attempt_exam_rules(
                attempt_id=attempt_id,
                student_id="support-student",
            )
            timeline = uow.audit_events.list_events("attempt", attempt_id)

        event_types = [event["event_type"] for event in timeline]
        self.assertTrue(q_issue["reported"])
        self.assertTrue(tech_issue["reported"])
        self.assertGreaterEqual(len(rules["rules"]), 3)
        self.assertIn("QUESTION_ISSUE_REPORTED", event_types)
        self.assertIn("TECHNICAL_ISSUE_REPORTED", event_types)

    def test_service_auto_submit_expired_attempt_for_student(self):
        exam_id = self._seed_exam()
        attempt_id = self._start_attempt(exam_id, "timeout-student")
        expired_ts = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        with UnitOfWork(self.db) as uow:
            uow.conn.execute(
                "UPDATE attempts SET expires_at = ? WHERE id = ?",
                (expired_ts, attempt_id),
            )

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            result = delivery.auto_submit_expired_attempt_for_student(
                attempt_id=attempt_id,
                student_id="timeout-student",
            )

        self.assertEqual(result["status"], "finalized")
        self.assertTrue(result["auto_submitted"])

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
    def test_student_support_endpoints(self):
        exam_id = self._seed_exam()
        app = create_app(db_path=self.db_path)
        with TestClient(app) as client:
            student_headers = {"x-student-id": "support-api-student"}
            admin_headers = {"x-admin": "true", "x-admin-id": "ops-admin"}
            started = client.post(
                f"/student/exams/{exam_id}/start",
                headers=student_headers,
            )
            self.assertEqual(started.status_code, 200)
            attempt_id = started.json()["data"]["attempt_id"]
            question_id = started.json()["data"]["first_question"]["question"]["id"]

            question_issue = client.post(
                f"/student/attempts/{attempt_id}/question-issue",
                headers=student_headers,
                json={
                    "question_id": question_id,
                    "issue_type": "clarity",
                    "note": "Question wording is ambiguous",
                },
            )
            technical_issue = client.post(
                f"/student/attempts/{attempt_id}/technical-issue",
                headers=student_headers,
                json={
                    "issue_type": "keyboard",
                    "note": "Key input delayed",
                },
            )
            rules_resp = client.get(
                f"/student/attempts/{attempt_id}/rules",
                headers=student_headers,
            )
            broadcast_resp = client.post(
                f"/admin/exams/{exam_id}/broadcast",
                headers=admin_headers,
                json={
                    "message": "System check complete. Continue calmly.",
                    "severity": "info",
                },
            )
            broadcasts = client.get(
                f"/student/attempts/{attempt_id}/broadcasts?limit=20",
                headers=student_headers,
            )
            expired_ts = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
            with UnitOfWork(self.db) as uow:
                uow.conn.execute(
                    "UPDATE attempts SET expires_at = ? WHERE id = ?",
                    (expired_ts, attempt_id),
                )
            auto_submit_resp = client.post(
                f"/student/attempts/{attempt_id}/auto-submit",
                headers=student_headers,
            )

        self.assertEqual(question_issue.status_code, 200)
        self.assertEqual(technical_issue.status_code, 200)
        self.assertEqual(rules_resp.status_code, 200)
        self.assertEqual(broadcast_resp.status_code, 200)
        self.assertEqual(broadcasts.status_code, 200)
        self.assertEqual(auto_submit_resp.status_code, 200)
        self.assertEqual(broadcast_resp.json()["data"]["severity"], "info")
        self.assertGreaterEqual(broadcasts.json()["data"]["count"], 1)
        self.assertTrue(auto_submit_resp.json()["data"]["auto_submitted"])


if __name__ == "__main__":
    unittest.main()
