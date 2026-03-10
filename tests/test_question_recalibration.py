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
from phase1_server.services.question_calibration_service import (
    QuestionCalibrationService,
    QuestionRecalibrationRollbackRequest,
    QuestionRecalibrationRequest,
)
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


class QuestionRecalibrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "recalibration.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _seed_exam(self) -> tuple[str, str, str]:
        with UnitOfWork(self.db) as uow:
            q_service = QuestionService(uow.questions)
            easy_q = q_service.create_question(
                QuestionCreatePayload(
                    text="Easy target",
                    topic="network",
                    difficulty="medium",
                    marks=2.0,
                    difficulty_level=5,
                    discrimination_index=0.4,
                    options=[("A-easy", True), ("B-easy", False), ("C-easy", False)],
                )
            )
            hard_q = q_service.create_question(
                QuestionCreatePayload(
                    text="Hard target",
                    topic="network",
                    difficulty="medium",
                    marks=2.0,
                    difficulty_level=5,
                    discrimination_index=0.4,
                    options=[("A-hard", True), ("B-hard", False), ("C-hard", False)],
                )
            )
            exam_service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
            exam = exam_service.create_exam(
                ExamCreatePayload(
                    name="Calibration Exam",
                    duration_minutes=30,
                    negative_marking=0,
                )
            )
            exam_service.add_questions(exam.id, [easy_q.id, hard_q.id])
            exam_service.publish_exam(exam.id)
        return exam.id, easy_q.id, hard_q.id

    def _run_attempt(self, exam_id: str, student_id: str, easy_q_id: str, hard_q_id: str) -> None:
        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                analytics_repo=uow.analytics,
                audit_service=AuditService(uow.audit_events),
            )
            started = delivery.start_attempt(exam_id, student_id)
            for sequence in (1, 2):
                question_payload = delivery.fetch_question(started["attempt_id"], sequence, student_id)
                q_id = question_payload["question"]["id"]
                if q_id == easy_q_id:
                    selected = next(
                        option
                        for option in question_payload["options"]
                        if option["option_text"].startswith("A-")
                    )
                elif q_id == hard_q_id:
                    selected = next(
                        option
                        for option in question_payload["options"]
                        if not option["option_text"].startswith("A-")
                    )
                else:
                    raise AssertionError("Unexpected question in snapshot")

                delivery.submit_answer(
                    AnswerSubmissionPayload(
                        attempt_id=started["attempt_id"],
                        question_id=q_id,
                        selected_option_id=selected["id"],
                    ),
                    student_id=student_id,
                )
            delivery.finalize_attempt(started["attempt_id"], student_id)

    def test_preview_does_not_persist_metadata(self):
        exam_id, easy_q_id, hard_q_id = self._seed_exam()
        self._run_attempt(exam_id, "stu-a", easy_q_id, hard_q_id)
        self._run_attempt(exam_id, "stu-b", easy_q_id, hard_q_id)

        with UnitOfWork(self.db) as uow:
            service = QuestionCalibrationService(
                uow.analytics,
                uow.questions,
                uow.exams,
                recalibration_repo=uow.recalibration_runs,
                audit_service=AuditService(uow.audit_events),
            )
            result = service.recalibrate_exam_questions(
                exam_id,
                QuestionRecalibrationRequest(min_attempts=2, apply=False, actor_id="admin-1"),
            )

            easy_after = uow.questions.get_question_with_options(easy_q_id)[0]
            hard_after = uow.questions.get_question_with_options(hard_q_id)[0]
            events = AuditService(uow.audit_events).list_entity_timeline("exam", exam_id)

        easy_item = next(item for item in result["items"] if item["question_id"] == easy_q_id)
        hard_item = next(item for item in result["items"] if item["question_id"] == hard_q_id)

        self.assertEqual(result["mode"], "preview")
        self.assertIsNotNone(result["run_id"])
        self.assertEqual(easy_item["suggested"]["difficulty_level"], 1)
        self.assertEqual(hard_item["suggested"]["difficulty_level"], 10)
        self.assertEqual(easy_after.difficulty_level, 5)
        self.assertEqual(hard_after.difficulty_level, 5)
        self.assertIn(
            "QUESTION_DIFFICULTY_RECALIBRATED",
            [item["event_type"] for item in events],
        )

    def test_apply_persists_metadata(self):
        exam_id, easy_q_id, hard_q_id = self._seed_exam()
        self._run_attempt(exam_id, "stu-a", easy_q_id, hard_q_id)
        self._run_attempt(exam_id, "stu-b", easy_q_id, hard_q_id)

        with UnitOfWork(self.db) as uow:
            service = QuestionCalibrationService(
                uow.analytics,
                uow.questions,
                uow.exams,
                recalibration_repo=uow.recalibration_runs,
                audit_service=AuditService(uow.audit_events),
            )
            result = service.recalibrate_exam_questions(
                exam_id,
                QuestionRecalibrationRequest(min_attempts=2, apply=True, actor_id="admin-2"),
            )

            easy_after = uow.questions.get_question_with_options(easy_q_id)[0]
            hard_after = uow.questions.get_question_with_options(hard_q_id)[0]

        self.assertEqual(result["mode"], "apply")
        self.assertIsNotNone(result["run_id"])
        self.assertEqual(result["updated_questions"], 2)
        self.assertEqual(easy_after.difficulty_level, 1)
        self.assertEqual(easy_after.difficulty, "easy")
        self.assertAlmostEqual(easy_after.discrimination_index, 0.0)
        self.assertEqual(hard_after.difficulty_level, 10)
        self.assertEqual(hard_after.difficulty, "hard")
        self.assertAlmostEqual(hard_after.discrimination_index, 0.0)

    def test_min_attempts_skips_updates(self):
        exam_id, easy_q_id, hard_q_id = self._seed_exam()
        self._run_attempt(exam_id, "stu-a", easy_q_id, hard_q_id)

        with UnitOfWork(self.db) as uow:
            service = QuestionCalibrationService(
                uow.analytics,
                uow.questions,
                uow.exams,
                recalibration_repo=uow.recalibration_runs,
                audit_service=AuditService(uow.audit_events),
            )
            result = service.recalibrate_exam_questions(
                exam_id,
                QuestionRecalibrationRequest(min_attempts=2, apply=True),
            )

        self.assertEqual(result["eligible_questions"], 0)
        self.assertEqual(result["updated_questions"], 0)
        self.assertTrue(
            all(item["status"] == "skipped_insufficient_attempts" for item in result["items"])
        )

    def test_history_lists_runs_with_items(self):
        exam_id, easy_q_id, hard_q_id = self._seed_exam()
        self._run_attempt(exam_id, "stu-a", easy_q_id, hard_q_id)
        self._run_attempt(exam_id, "stu-b", easy_q_id, hard_q_id)

        with UnitOfWork(self.db) as uow:
            service = QuestionCalibrationService(
                uow.analytics,
                uow.questions,
                uow.exams,
                recalibration_repo=uow.recalibration_runs,
                audit_service=AuditService(uow.audit_events),
            )
            preview = service.recalibrate_exam_questions(
                exam_id,
                QuestionRecalibrationRequest(min_attempts=2, apply=False, actor_id="admin-3"),
            )
            apply_run = service.recalibrate_exam_questions(
                exam_id,
                QuestionRecalibrationRequest(min_attempts=2, apply=True, actor_id="admin-3"),
            )
            history = service.list_recalibration_history(exam_id)
            detail = service.get_recalibration_run(exam_id, apply_run["run_id"])

        self.assertEqual(history["exam_id"], exam_id)
        self.assertGreaterEqual(len(history["runs"]), 2)
        self.assertIn(
            apply_run["run_id"],
            [row["run_id"] for row in history["runs"]],
        )
        self.assertIn(
            preview["run_id"],
            [row["run_id"] for row in history["runs"]],
        )
        self.assertEqual(detail["run"]["run_id"], apply_run["run_id"])
        self.assertEqual(len(detail["items"]), 2)

    def test_rollback_restores_original_metadata(self):
        exam_id, easy_q_id, hard_q_id = self._seed_exam()
        self._run_attempt(exam_id, "stu-a", easy_q_id, hard_q_id)
        self._run_attempt(exam_id, "stu-b", easy_q_id, hard_q_id)

        with UnitOfWork(self.db) as uow:
            service = QuestionCalibrationService(
                uow.analytics,
                uow.questions,
                uow.exams,
                recalibration_repo=uow.recalibration_runs,
                audit_service=AuditService(uow.audit_events),
            )
            apply_run = service.recalibrate_exam_questions(
                exam_id,
                QuestionRecalibrationRequest(min_attempts=2, apply=True, actor_id="admin-4"),
            )
            rollback = service.rollback_recalibration_run(
                exam_id,
                apply_run["run_id"],
                QuestionRecalibrationRollbackRequest(
                    actor_id="admin-4",
                    reason="policy rollback",
                ),
            )

            easy_after = uow.questions.get_question_with_options(easy_q_id)[0]
            hard_after = uow.questions.get_question_with_options(hard_q_id)[0]

            history = service.list_recalibration_history(exam_id)

        self.assertEqual(rollback["mode"], "rollback")
        self.assertEqual(rollback["source_run_id"], apply_run["run_id"])
        self.assertEqual(rollback["updated_questions"], 2)
        self.assertEqual(easy_after.difficulty, "medium")
        self.assertEqual(easy_after.difficulty_level, 5)
        self.assertAlmostEqual(easy_after.discrimination_index, 0.4)
        self.assertEqual(hard_after.difficulty, "medium")
        self.assertEqual(hard_after.difficulty_level, 5)
        self.assertAlmostEqual(hard_after.discrimination_index, 0.4)
        rollback_run = next(row for row in history["runs"] if row["run_id"] == rollback["run_id"])
        self.assertEqual(rollback_run["mode"], "rollback")
        self.assertEqual(rollback_run["source_run_id"], apply_run["run_id"])

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
    def test_admin_recalibration_endpoint(self):
        exam_id, easy_q_id, hard_q_id = self._seed_exam()
        self._run_attempt(exam_id, "stu-a", easy_q_id, hard_q_id)
        self._run_attempt(exam_id, "stu-b", easy_q_id, hard_q_id)

        app = create_app(db_path=self.db_path)
        with TestClient(app) as client:
            response = client.post(
                f"/admin/exams/{exam_id}/questions/recalibrate",
                headers={"x-admin": "true", "x-admin-id": "api-admin"},
                json={"min_attempts": 2, "apply": True},
            )
            self.assertEqual(response.status_code, 200)
            run_id = response.json()["data"]["run_id"]

            history = client.get(
                f"/admin/exams/{exam_id}/questions/recalibration-runs",
                headers={"x-admin": "true"},
            )
            detail = client.get(
                f"/admin/exams/{exam_id}/questions/recalibration-runs/{run_id}",
                headers={"x-admin": "true"},
            )
            rollback = client.post(
                f"/admin/exams/{exam_id}/questions/recalibration-runs/{run_id}/rollback",
                headers={"x-admin": "true", "x-admin-id": "api-admin"},
                json={"reason": "api rollback"},
            )

        payload = response.json()["data"]
        self.assertEqual(payload["mode"], "apply")
        self.assertEqual(payload["updated_questions"], 2)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(rollback.status_code, 200)
        self.assertEqual(rollback.json()["data"]["mode"], "rollback")


if __name__ == "__main__":
    unittest.main()
