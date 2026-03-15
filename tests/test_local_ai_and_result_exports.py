import tempfile
import unittest
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import (
    AnswerSubmissionPayload,
    DeliveryService,
)
from phase1_server.services.exam_service import ExamCreatePayload, ExamService
from phase1_server.services.question_service import QuestionCreatePayload, QuestionService
from phase1_server.settings import AppSettings
from phase1_server.uow import UnitOfWork

try:
    from fastapi.testclient import TestClient
    from phase1_server.app import create_app

    FASTAPI_AVAILABLE = True
except Exception:
    TestClient = None
    create_app = None
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
class LocalAIAndResultExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "local_ai_and_results.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _admin_headers(self, admin_id: str = "superadmin") -> dict[str, str]:
        return {
            "x-admin": "true",
            "x-admin-id": admin_id,
        }

    def _create_app(self) -> "TestClient":
        app = create_app(
            settings=AppSettings(
                db_path=self.db_path,
                ai_mode="local_sidecar",
                ai_base_url="http://127.0.0.1:9",
                ai_timeout_seconds=1,
                ai_model_name="qwen2.5:7b-instruct",
            )
        )
        return TestClient(app)

    def _seed_subjective_exam(self) -> tuple[str, str]:
        with UnitOfWork(self.db) as uow:
            question = QuestionService(uow.questions).create_question(
                QuestionCreatePayload(
                    text="What is a database management system and how does it work?",
                    topic="databases",
                    difficulty="medium",
                    marks=4,
                    question_type="short_answer",
                    word_target_min=20,
                    word_target_max=60,
                    word_hard_max=90,
                )
            )
            exam_service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
            exam = exam_service.create_exam(
                ExamCreatePayload(
                    name="NITMEXS Subjective Review Exam",
                    duration_minutes=30,
                    negative_marking=0.0,
                )
            )
            exam_service.add_questions(exam.id, [question.id])
            exam_service.publish_exam(exam.id)
            return exam.id, question.id

    def _seed_mcq_exam(self) -> tuple[str, str]:
        with UnitOfWork(self.db) as uow:
            question = QuestionService(uow.questions).create_question(
                QuestionCreatePayload(
                    text="SQLite supports WAL mode.",
                    topic="databases",
                    difficulty="easy",
                    marks=1,
                    question_type="true_false",
                    options=[("True", True)],
                )
            )
            exam_service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
            exam = exam_service.create_exam(
                ExamCreatePayload(
                    name="NITMEXS Objective Result Exam",
                    duration_minutes=15,
                    negative_marking=0.0,
                )
            )
            exam_service.add_questions(exam.id, [question.id])
            exam_service.publish_exam(exam.id)
            return exam.id, question.id

    def _start_attempt(self, exam_id: str, student_id: str) -> str:
        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            return delivery.start_attempt(exam_id, student_id)["attempt_id"]

    def test_admin_ai_status_and_refine_route_gracefully_fallback(self):
        with self._create_app() as client:
            status_resp = client.get("/admin/ai/status", headers=self._admin_headers())
            refine_resp = client.post(
                "/admin/ai/question-refine",
                headers=self._admin_headers(),
                json={
                    "question_text": "Define DBMS.",
                    "question_type": "short_answer",
                    "topic": "databases",
                    "marks": 2,
                },
            )

        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(refine_resp.status_code, 200)
        self.assertEqual(status_resp.json()["data"]["provider"], "local_http")
        self.assertFalse(status_resp.json()["data"]["reachable"])
        self.assertEqual(refine_resp.json()["data"]["provider"], "heuristic")
        self.assertIn("rewritten_question", refine_resp.json()["data"])

        with UnitOfWork(self.db) as uow:
            events = uow.audit_events.search_events(
                entity_type="ai",
                entity_id="question_refine",
                event_type="AI_QUESTION_REFINED",
                limit=10,
            )
        self.assertGreaterEqual(len(events), 1)

    def test_publish_results_is_blocked_while_subjective_review_is_pending(self):
        exam_id, question_id = self._seed_subjective_exam()
        attempt_id = self._start_attempt(exam_id, "cadet-review-pending")

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            delivery.submit_answer(
                AnswerSubmissionPayload(
                    attempt_id=attempt_id,
                    question_id=question_id,
                    text_answer="A DBMS stores data, organizes records, and provides controlled retrieval through queries.",
                ),
                "cadet-review-pending",
            )
            delivery.finalize_attempt(attempt_id, "cadet-review-pending")

        with self._create_app() as client:
            publish_resp = client.post(
                f"/admin/exams/{exam_id}/results/publish",
                headers=self._admin_headers(),
            )
            pending_csv_resp = client.get(
                f"/admin/exams/{exam_id}/results/pending-review.csv",
                headers=self._admin_headers(),
            )

        self.assertEqual(publish_resp.status_code, 400)
        self.assertIn("pending", publish_resp.json()["detail"].lower())
        self.assertEqual(pending_csv_resp.status_code, 200)
        self.assertIn("queue_type", pending_csv_resp.text)
        self.assertIn("subjective_review", pending_csv_resp.text)

    def test_review_publish_preview_pdf_csv_and_artifacts_workflow(self):
        exam_id, question_id = self._seed_subjective_exam()
        attempt_id = self._start_attempt(exam_id, "cadet-reviewed")

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            delivery.submit_answer(
                AnswerSubmissionPayload(
                    attempt_id=attempt_id,
                    question_id=question_id,
                    text_answer=(
                        "A database management system stores, secures, updates, and retrieves data "
                        "through structured tables, query processing, and access control."
                    ),
                ),
                "cadet-reviewed",
            )
            delivery.finalize_attempt(attempt_id, "cadet-reviewed")

        with self._create_app() as client:
            queue_resp = client.get(
                f"/admin/exams/{exam_id}/subjective-review-queue",
                headers=self._admin_headers(),
            )
            self.assertEqual(queue_resp.status_code, 200)
            self.assertEqual(len(queue_resp.json()["data"]), 1)

            review_resp = client.post(
                f"/admin/attempts/{attempt_id}/subjective-review",
                headers=self._admin_headers(),
                json={
                    "question_id": question_id,
                    "marks_awarded": 3.5,
                    "review_note": "Good conceptual coverage.",
                },
            )
            publish_resp = client.post(
                f"/admin/exams/{exam_id}/results/publish",
                headers=self._admin_headers(),
            )
            results_resp = client.get(
                f"/admin/exams/{exam_id}/results",
                headers=self._admin_headers(),
            )
            preview_resp = client.get(
                f"/admin/attempts/{attempt_id}/result-preview",
                headers=self._admin_headers(),
            )
            pdf_resp = client.get(
                f"/admin/attempts/{attempt_id}/result-sheet.pdf",
                headers=self._admin_headers(),
            )
            csv_resp = client.get(
                f"/admin/exams/{exam_id}/results/export.csv",
                headers=self._admin_headers(),
            )
            artifacts_resp = client.get(
                f"/admin/artifacts?exam_id={exam_id}",
                headers=self._admin_headers(),
            )

        self.assertEqual(review_resp.status_code, 200)
        self.assertEqual(publish_resp.status_code, 200)
        self.assertEqual(results_resp.status_code, 200)
        self.assertTrue(results_resp.json()["data"]["results_published"])
        self.assertEqual(results_resp.json()["data"]["pending_review_count"], 0)
        self.assertEqual(preview_resp.status_code, 200)
        self.assertIn("NITMEXS Result Sheet", preview_resp.text)
        self.assertIn("Candidate Result Sheet", preview_resp.text)
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertTrue(pdf_resp.content.startswith(b"%PDF-1.4"))
        self.assertEqual(csv_resp.status_code, 200)
        self.assertIn("exam_name", csv_resp.text)
        self.assertIn("cadet-reviewed", csv_resp.text)
        self.assertEqual(artifacts_resp.status_code, 200)
        artifact_types = {item["artifact_type"] for item in artifacts_resp.json()["data"]}
        self.assertIn("result_preview_html", artifact_types)
        self.assertIn("result_sheet_pdf", artifact_types)
        self.assertIn("exam_results_csv", artifact_types)


if __name__ == "__main__":
    unittest.main()
