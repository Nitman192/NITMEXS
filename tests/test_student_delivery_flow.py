import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from phase1_server.db import Database, SQLiteConfig
from phase1_server.models import AttemptStatus
from phase1_server.services.delivery_service import (
    AnswerSubmissionPayload,
    AttemptStateError,
    DeliveryError,
    DeliveryService,
)
from phase1_server.services.exam_service import ExamCreatePayload, ExamService
from phase1_server.services.question_service import QuestionCreatePayload, QuestionService
from phase1_server.uow import UnitOfWork


class FrozenClock:
    def __init__(self, start: datetime):
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: int) -> None:
        self.current = self.current + timedelta(seconds=seconds)


class StudentDeliveryFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db")
        self.db = Database(SQLiteConfig(db_path=self.tmp.name))
        self.db.initialize()

    def tearDown(self):
        self.tmp.close()

    def _seed_exam(self, duration_minutes: int = 30) -> tuple[str, list[str]]:
        with UnitOfWork(self.db) as uow:
            q_service = QuestionService(uow.questions)
            question_ids = []
            for idx in range(3):
                question = q_service.create_question(
                    QuestionCreatePayload(
                        text=f"Question {idx}",
                        topic="topic",
                        difficulty="easy",
                        marks=1.0,
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
                    negative_marking=0,
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
            self.assertEqual(attempt.status, AttemptStatus.FINALIZED)


if __name__ == "__main__":
    unittest.main()
