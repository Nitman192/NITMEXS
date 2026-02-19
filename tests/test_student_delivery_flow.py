import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from phase1_server.db import Database, SQLiteConfig
from phase1_server.models import Attempt, AttemptStatus
from phase1_server.services.delivery_service import (
    AnswerSubmissionPayload,
    AttemptStateError,
    DeliveryError,
    DeliveryService,
    OwnershipError,
)
from phase1_server.services.exam_service import (
    ExamCreatePayload,
    ExamService,
    ExamValidationError,
)
from phase1_server.services.grading_service import (
    GradingOwnershipError,
    ResultNotReadyError,
)
from phase1_server.services.question_service import QuestionCreatePayload, QuestionService
from phase1_server.uow import UnitOfWork


class FrozenClock:
    def __init__(self, start: datetime):
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: int) -> None:
        self.current = self.current + timedelta(seconds=seconds)




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


class StudentDeliveryFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db")
        self.db = Database(SQLiteConfig(db_path=self.tmp.name))
        self.db.initialize()

    def tearDown(self):
        self.tmp.close()

    def _seed_exam(
        self,
        duration_minutes: int = 30,
        negative_marking: float = 0,
    ) -> tuple[str, list[str]]:
        with UnitOfWork(self.db) as uow:
            q_service = QuestionService(uow.questions)
            question_ids = []
            for idx in range(3):
                question = q_service.create_question(
                    QuestionCreatePayload(
                        text=f"Question {idx}",
                        topic="topic",
                        difficulty="easy",
                        marks=2.0,
                        options=[
                            (f"A{idx}", True),
                            (f"B{idx}", False),
                            (f"C{idx}", False),
                        ],
                    )
                )
                question_ids.append(question.id)

            e_service = ExamService(uow.exams, uow.questions)
            exam = e_service.create_exam(
                ExamCreatePayload(
                    name="Delivery Exam",
                    duration_minutes=duration_minutes,
                    negative_marking=negative_marking,
                )
            )
            e_service.add_questions(exam.id, question_ids)
            e_service.publish_exam(exam.id)

        return exam.id, question_ids

    def test_attempt_start(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            data = service.start_attempt(exam_id=exam_id, student_id="s1")
            attempt = uow.attempts.get(data["attempt_id"])

        self.assertEqual(data["status"], AttemptStatus.ACTIVE.value)
        self.assertEqual(attempt.status, AttemptStatus.ACTIVE)
        self.assertIn("first_question", data)
        self.assertIn("started_at", data)
        self.assertIn("expires_at", data)

    def test_snapshot_linkage_and_question_fetch(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id=exam_id, student_id="s2")
            attempt_id = start["attempt_id"]
            question = service.fetch_question(
                attempt_id=attempt_id,
                sequence_number=1,
                student_id="s2",
            )

        self.assertEqual(question["attempt_id"], attempt_id)
        self.assertEqual(question["sequence_number"], 1)
        self.assertIn("options", question)
        self.assertNotIn("is_correct", question["options"][0])

    def test_answer_submission_validation(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id=exam_id, student_id="s3")
            question = service.fetch_question(start["attempt_id"], 1, "s3")
            option_id = question["options"][0]["id"]

            submitted = service.submit_answer(
                AnswerSubmissionPayload(
                    attempt_id=start["attempt_id"],
                    question_id=question["question"]["id"],
                    selected_option_id=option_id,
                ),
                student_id="s3",
            )
            submitted_again = service.submit_answer(
                AnswerSubmissionPayload(
                    attempt_id=start["attempt_id"],
                    question_id=question["question"]["id"],
                    selected_option_id=option_id,
                ),
                student_id="s3",
            )

        self.assertEqual(submitted["question_id"], question["question"]["id"])
        self.assertTrue(submitted_again["idempotent"])

    def test_invalid_state_transitions(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id=exam_id, student_id="s4")
            service.finalize_attempt(start["attempt_id"], student_id="s4")

            with self.assertRaises(AttemptStateError):
                service.fetch_question(start["attempt_id"], 1, "s4")

            second_finalize = service.finalize_attempt(start["attempt_id"], student_id="s4")
            self.assertEqual(second_finalize["status"], AttemptStatus.FINALIZED.value)

            with self.assertRaises(AttemptStateError):
                service.submit_answer(
                    AnswerSubmissionPayload(
                        attempt_id=start["attempt_id"],
                        question_id="missing-question",
                        selected_option_id="missing-option",
                    ),
                    student_id="s4",
                )

    def test_ownership_enforcement(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id=exam_id, student_id="owner")
            with self.assertRaises(DeliveryError):
                service.fetch_question(start["attempt_id"], 1, "other-student")

    def test_auto_expiration_on_submit(self):
        exam_id, _ = self._seed_exam(duration_minutes=1)
        clock = FrozenClock(datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc))

        with UnitOfWork(self.db) as uow:
            service = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                now_provider=clock.now,
            )
            start = service.start_attempt(exam_id=exam_id, student_id="timed")
            question = service.fetch_question(start["attempt_id"], 1, "timed")
            clock.advance(seconds=61)

            with self.assertRaises(AttemptStateError):
                service.submit_answer(
                    AnswerSubmissionPayload(
                        attempt_id=start["attempt_id"],
                        question_id=question["question"]["id"],
                        selected_option_id=question["options"][0]["id"],
                    ),
                    student_id="timed",
                )

            attempt = uow.attempts.get(start["attempt_id"])
            self.assertEqual(attempt.status, AttemptStatus.ACTIVE)


    def test_audit_log_created_on_finalize_and_grading(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id, "audit1")
            service.finalize_attempt(start["attempt_id"], "audit1")
            events = uow.attempts.list_audit_events(start["attempt_id"])

        event_types = [event["event_type"] for event in events]
        self.assertIn("FINALIZED", event_types)
        self.assertIn("GRADED", event_types)

    def test_result_all_correct(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id, "r1")
            for seq in [1, 2, 3]:
                q = service.fetch_question(start["attempt_id"], seq, "r1")
                correct_option = next(
                    option for option in q["options"] if option["option_text"].startswith("A")
                )
                service.submit_answer(
                    AnswerSubmissionPayload(
                        attempt_id=start["attempt_id"],
                        question_id=q["question"]["id"],
                        selected_option_id=correct_option["id"],
                    ),
                    "r1",
                )

            finalized = service.finalize_attempt(start["attempt_id"], "r1")
            result = service.get_result(start["attempt_id"], "r1")
            audit_events = uow.attempts.list_audit_events(start["attempt_id"])

        self.assertEqual(finalized["grading"], "completed")
        self.assertEqual(result["total_score"], result["total_possible_marks"])
        self.assertTrue(result["passed"])
        event_types = [event["event_type"] for event in audit_events]
        self.assertIn("FINALIZED", event_types)
        self.assertIn("GRADED", event_types)
        self.assertIn("RESULT_VIEWED", event_types)

    def test_result_all_wrong_with_negative_marking(self):
        exam_id, _ = self._seed_exam(negative_marking=0.5)
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id, "r2")
            for seq in [1, 2, 3]:
                q = service.fetch_question(start["attempt_id"], seq, "r2")
                wrong_option = next(
                    option for option in q["options"]
                    if not option["option_text"].startswith("A")
                )
                service.submit_answer(
                    AnswerSubmissionPayload(
                        attempt_id=start["attempt_id"],
                        question_id=q["question"]["id"],
                        selected_option_id=wrong_option["id"],
                    ),
                    "r2",
                )

            service.finalize_attempt(start["attempt_id"], "r2")
            result = service.get_result(start["attempt_id"], "r2")

        self.assertEqual(result["total_score"], -1.5)
        self.assertFalse(result["passed"])


    def test_finalize_attempt_twice_is_idempotent(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id, "idem1")
            first = service.finalize_attempt(start["attempt_id"], "idem1")
            second = service.finalize_attempt(start["attempt_id"], "idem1")
            stored = uow.attempts.get_attempt_result(start["attempt_id"])

        self.assertEqual(first["status"], AttemptStatus.FINALIZED.value)
        self.assertEqual(second["status"], AttemptStatus.FINALIZED.value)
        self.assertEqual(first["result"], second["result"])
        self.assertEqual(first["finalized_at"], second["finalized_at"])
        self.assertIsNotNone(stored)


    def test_finalize_with_stale_version_raises_concurrency_error(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id, "conc1")
            stale = uow.attempts.get(start["attempt_id"])
            self.assertIsNotNone(stale)
            stale_attempt = Attempt(
                id=stale.id,
                candidate_id=stale.candidate_id,
                exam_id=stale.exam_id,
                status=stale.status,
                created_at=stale.created_at,
                updated_at=stale.updated_at,
                version=stale.version,
                submitted_at=stale.submitted_at,
                expires_at=stale.expires_at,
            )

            first = service.finalize_attempt(start["attempt_id"], "conc1")
            stale_repo = StaleAttemptRepository(uow.attempts, stale_attempt)
            stale_service = DeliveryService(stale_repo, uow.exams, uow.questions)

            with self.assertRaises(AttemptStateError):
                stale_service.finalize_attempt(start["attempt_id"], "conc1")

            second = service.finalize_attempt(start["attempt_id"], "conc1")
            events = uow.attempts.list_audit_events(start["attempt_id"])

        self.assertEqual(first["result"], second["result"])
        self.assertEqual(1, len([e for e in events if e["event_type"] == "GRADED"]))

    def test_finalize_duplicate_call_grades_once(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id, "idem2")
            service.finalize_attempt(start["attempt_id"], "idem2")
            summary_before = uow.attempts.get_attempt_result(start["attempt_id"])
            question_results_before = uow.attempts.get_question_results(start["attempt_id"])

            # Simulate near-concurrent duplicate finalize call as sequential re-entry.
            service.finalize_attempt(start["attempt_id"], "idem2")

            summary_after = uow.attempts.get_attempt_result(start["attempt_id"])
            question_results_after = uow.attempts.get_question_results(start["attempt_id"])

        self.assertEqual(summary_before, summary_after)
        self.assertEqual(len(question_results_before), len(question_results_after))
        self.assertEqual(question_results_before, question_results_after)



    def test_finalize_attempt_fails_after_expiration_without_force(self):
        exam_id, _ = self._seed_exam(duration_minutes=1)
        clock = FrozenClock(datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc))

        with UnitOfWork(self.db) as uow:
            service = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                now_provider=clock.now,
            )
            start = service.start_attempt(exam_id, "late1")
            clock.advance(seconds=61)
            with self.assertRaises(AttemptStateError):
                service.finalize_attempt(start["attempt_id"], "late1")

    def test_force_finalize_expired_attempt_runs_grading_once(self):
        exam_id, _ = self._seed_exam(duration_minutes=1)
        clock = FrozenClock(datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc))

        with UnitOfWork(self.db) as uow:
            service = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                now_provider=clock.now,
            )
            start = service.start_attempt(exam_id, "late2")
            clock.advance(seconds=61)

            first = service.force_finalize_expired_attempt(start["attempt_id"])
            summary_before = uow.attempts.get_attempt_result(start["attempt_id"])
            question_before = uow.attempts.get_question_results(start["attempt_id"])

            second = service.force_finalize_expired_attempt(start["attempt_id"])
            summary_after = uow.attempts.get_attempt_result(start["attempt_id"])
            question_after = uow.attempts.get_question_results(start["attempt_id"])
            events = uow.attempts.list_audit_events(start["attempt_id"])

        self.assertEqual(first["status"], AttemptStatus.FINALIZED.value)
        self.assertEqual(second["result"], first["result"])
        self.assertEqual(summary_before, summary_after)
        self.assertEqual(question_before, question_after)
        event_types = [event["event_type"] for event in events]
        self.assertIn("FINALIZED", event_types)
        self.assertIn("GRADED", event_types)

    def test_audit_log_created_on_result_view(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id, "audit2")
            service.finalize_attempt(start["attempt_id"], "audit2")
            service.get_result(start["attempt_id"], "audit2")
            events = uow.attempts.list_audit_events(start["attempt_id"])

        self.assertIn("RESULT_VIEWED", [event["event_type"] for event in events])

    def test_result_unauthorized_access(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id, "owner1")
            service.finalize_attempt(start["attempt_id"], "owner1")
            with self.assertRaises(GradingOwnershipError):
                service.get_result(start["attempt_id"], "intruder")

    def test_result_before_finalize_fails(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id, "r3")
            with self.assertRaises(ResultNotReadyError):
                service.get_result(start["attempt_id"], "r3")


    def test_closed_exam_prevents_new_attempts(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            exam_service = ExamService(uow.exams, uow.questions)
            exam_service.close_exam(exam_id, actor_id="admin1")
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            with self.assertRaises(ExamValidationError):
                service.start_attempt(exam_id=exam_id, student_id="blocked")

    def test_closed_exam_allows_result_viewing_for_existing_attempt(self):
        exam_id, _ = self._seed_exam()
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(uow.attempts, uow.exams, uow.questions)
            start = service.start_attempt(exam_id, "closed-ok")
            service.finalize_attempt(start["attempt_id"], "closed-ok")
            exam_service = ExamService(uow.exams, uow.questions)
            exam_service.close_exam(exam_id, actor_id="admin1")

            result = service.get_result(start["attempt_id"], "closed-ok")

        self.assertIn("total_score", result)


if __name__ == "__main__":
    unittest.main()
