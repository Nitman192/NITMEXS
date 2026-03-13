import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import AnswerSubmissionPayload, DeliveryService
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

    def test_service_broadcast_read_receipts(self):
        exam_id = self._seed_exam()
        attempt_id = self._start_attempt(exam_id, "receipt-student")

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            delivery.publish_exam_broadcast(
                exam_id=exam_id,
                message="Receipt check broadcast",
                severity="warn",
                actor_id="ops-admin",
            )
            broadcasts = delivery.list_attempt_broadcasts(
                attempt_id=attempt_id,
                student_id="receipt-student",
                limit=10,
            )
            broadcast_id = broadcasts["broadcasts"][0]["id"]
            first_ack = delivery.acknowledge_attempt_broadcasts(
                attempt_id=attempt_id,
                student_id="receipt-student",
                broadcast_ids=[broadcast_id],
            )
            second_ack = delivery.acknowledge_attempt_broadcasts(
                attempt_id=attempt_id,
                student_id="receipt-student",
                broadcast_ids=[broadcast_id],
            )
            exam_timeline = uow.audit_events.list_events("exam", exam_id)

        receipt_events = [
            event for event in exam_timeline if event["event_type"] == "BROADCAST_RECEIVED"
        ]
        self.assertEqual(first_ack["acknowledged_count"], 1)
        self.assertEqual(first_ack["already_acknowledged_count"], 0)
        self.assertEqual(second_ack["acknowledged_count"], 0)
        self.assertEqual(second_ack["already_acknowledged_count"], 1)
        self.assertEqual(len(receipt_events), 1)

    def test_service_result_analysis_and_ai_explanation(self):
        exam_id = self._seed_exam()
        attempt_id = self._start_attempt(exam_id, "analysis-student")

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            question_payload = delivery.fetch_question(attempt_id, 1, "analysis-student")
            wrong_option = next(
                option
                for option in question_payload["options"]
                if option["option_text"] != "A"
            )
            delivery.submit_answer(
                AnswerSubmissionPayload(
                    attempt_id=attempt_id,
                    question_id=question_payload["question"]["id"],
                    selected_option_id=wrong_option["id"],
                ),
                "analysis-student",
            )
            delivery.finalize_attempt(attempt_id, "analysis-student")
            result = delivery.get_result(attempt_id, "analysis-student")
            analysis = delivery.get_attempt_analysis(attempt_id, "analysis-student")
            explanation = delivery.explain_attempt_question(
                attempt_id,
                question_payload["question"]["id"],
                "analysis-student",
            )
            audit_events = uow.attempts.list_audit_events(attempt_id)

        self.assertEqual(result["exam_id"], exam_id)
        self.assertEqual(result["question_results"][0]["status"], "incorrect")
        self.assertEqual(result["question_results"][0]["question_text"], "Support feature question")
        self.assertEqual(analysis["question_count"], 1)
        self.assertEqual(
            analysis["incorrect_or_skipped_questions"][0]["question_id"],
            question_payload["question"]["id"],
        )
        self.assertIn("provider_status", analysis)
        self.assertIn("reason", analysis["provider_status"])
        self.assertIn("study_tip", explanation["analysis"])
        self.assertIn(explanation["provider"], {"heuristic", "openai", "gemini"})
        self.assertIn("provider_status", explanation)
        self.assertIn("reason", explanation["provider_status"])
        event_types = [event["event_type"] for event in audit_events]
        self.assertIn("RESULT_ANALYSIS_VIEWED", event_types)
        self.assertIn("AI_EXPLANATION_GENERATED", event_types)

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
            broadcast_ids = [
                row["id"] for row in broadcasts.json()["data"]["broadcasts"]
            ]
            ack_broadcasts = client.post(
                f"/student/attempts/{attempt_id}/broadcasts/ack",
                headers=student_headers,
                json={"broadcast_ids": broadcast_ids},
            )
            broadcast_receipts = client.get(
                (
                    f"/admin/audit/events?entity_type=exam&entity_id={exam_id}"
                    "&event_type=BROADCAST_RECEIVED&limit=50"
                ),
                headers=admin_headers,
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

            analysis_exam_id = self._seed_exam()
            analysis_started = client.post(
                f"/student/exams/{analysis_exam_id}/start",
                headers=student_headers,
            )
            self.assertEqual(analysis_started.status_code, 200)
            analysis_attempt_id = analysis_started.json()["data"]["attempt_id"]
            analysis_question = analysis_started.json()["data"]["first_question"]
            wrong_option = next(
                option
                for option in analysis_question["options"]
                if option["option_text"] != "A"
            )
            answer_resp = client.post(
                f"/student/attempts/{analysis_attempt_id}/answers",
                headers=student_headers,
                json={
                    "question_id": analysis_question["question"]["id"],
                    "selected_option_id": wrong_option["id"],
                },
            )
            finalize_resp = client.post(
                f"/student/attempts/{analysis_attempt_id}/finalize",
                headers=student_headers,
            )
            result_resp = client.get(
                f"/student/attempts/{analysis_attempt_id}/result",
                headers=student_headers,
            )
            analysis_resp = client.get(
                f"/student/attempts/{analysis_attempt_id}/analysis",
                headers=student_headers,
            )
            explain_resp = client.post(
                f"/student/attempts/{analysis_attempt_id}/analysis/explain",
                headers=student_headers,
                json={"question_id": analysis_question["question"]["id"]},
            )

        self.assertEqual(question_issue.status_code, 200)
        self.assertEqual(technical_issue.status_code, 200)
        self.assertEqual(rules_resp.status_code, 200)
        self.assertEqual(broadcast_resp.status_code, 200)
        self.assertEqual(broadcasts.status_code, 200)
        self.assertEqual(ack_broadcasts.status_code, 200)
        self.assertEqual(broadcast_receipts.status_code, 200)
        self.assertEqual(auto_submit_resp.status_code, 200)
        self.assertEqual(broadcast_resp.json()["data"]["severity"], "info")
        self.assertGreaterEqual(broadcasts.json()["data"]["count"], 1)
        self.assertGreaterEqual(ack_broadcasts.json()["data"]["acknowledged_count"], 1)
        self.assertGreaterEqual(broadcast_receipts.json()["data"]["count"], 1)
        self.assertTrue(auto_submit_resp.json()["data"]["auto_submitted"])
        self.assertEqual(answer_resp.status_code, 200)
        self.assertEqual(finalize_resp.status_code, 200)
        self.assertEqual(result_resp.status_code, 200)
        self.assertEqual(analysis_resp.status_code, 200)
        self.assertEqual(explain_resp.status_code, 200)
        self.assertEqual(
            result_resp.json()["data"]["question_results"][0]["status"],
            "incorrect",
        )
        self.assertEqual(analysis_resp.json()["data"]["question_count"], 1)
        self.assertIn("provider_status", analysis_resp.json()["data"])
        self.assertIn(
            explain_resp.json()["data"]["analysis"]["provider"],
            {"heuristic", "openai", "gemini"},
        )
        self.assertIn("provider_status", explain_resp.json()["data"])


if __name__ == "__main__":
    unittest.main()
