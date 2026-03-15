import tempfile
import unittest
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import (
    AnswerSubmissionPayload,
    DeliveryError,
    DeliveryService,
)
from phase1_server.services.exam_service import ExamCreatePayload, ExamService
from phase1_server.services.question_service import (
    QuestionCreatePayload,
    QuestionService,
)
from phase1_server.services.review_service import ReviewService
from phase1_server.uow import UnitOfWork


class ArmyBasicTextQuestionFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "army_basic_text_flow.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _create_exam_with_questions(self, payloads, negative_marking=0.0):
        with UnitOfWork(self.db) as uow:
            question_service = QuestionService(uow.questions)
            audit_service = AuditService(uow.audit_events)
            exam_service = ExamService(uow.exams, uow.questions, audit_service)
            question_ids = [
                question_service.create_question(payload).id for payload in payloads
            ]
            exam = exam_service.create_exam(
                ExamCreatePayload(
                    name="Army Basic Text Flow Exam",
                    duration_minutes=30,
                    negative_marking=negative_marking,
                )
            )
            exam_service.add_questions(exam.id, question_ids)
            exam_service.publish_exam(exam.id)
            return exam.id, question_ids

    def _start_attempt(self, exam_id: str, student_id: str):
        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            return delivery.start_attempt(exam_id, student_id)

    def test_question_service_supports_true_false_fib_and_subjective_types(self):
        exam_id, question_ids = self._create_exam_with_questions(
            [
                QuestionCreatePayload(
                    text="SQLite WAL improves concurrent read access.",
                    topic="databases",
                    difficulty="easy",
                    marks=1,
                    question_type="true_false",
                    options=[("True", True)],
                ),
                QuestionCreatePayload(
                    text="MS Access reports ka use ______ ke liye hota hai.",
                    topic="ms-access",
                    difficulty="easy",
                    marks=2,
                    question_type="fib_text",
                    accepted_answers=[
                        "data print karne ke liye",
                        "data summarize karne ke liye",
                    ],
                ),
                QuestionCreatePayload(
                    text="What is a database management system?",
                    topic="databases",
                    difficulty="medium",
                    marks=4,
                    question_type="short_answer",
                    word_target_min=20,
                    word_target_max=50,
                    word_hard_max=80,
                ),
                QuestionCreatePayload(
                    text="Explain how a database management system works in an organization.",
                    topic="databases",
                    difficulty="medium",
                    marks=8,
                    question_type="long_answer",
                    word_target_min=80,
                    word_target_max=150,
                    word_hard_max=220,
                ),
            ]
        )

        with UnitOfWork(self.db) as uow:
            questions = QuestionService(uow.questions).list_questions()
            stored_exam = uow.exams.get_exam(exam_id)

        self.assertIsNotNone(stored_exam)
        self.assertEqual(len(question_ids), 4)
        type_map = {item["question_type"]: item for item in questions}
        self.assertIn("true_false", type_map)
        self.assertEqual(
            [opt["option_text"] for opt in type_map["true_false"]["options"]],
            ["True", "False"],
        )
        self.assertIn("fib_text", type_map)
        self.assertEqual(len(type_map["fib_text"]["accepted_answers"]), 2)
        self.assertEqual(type_map["short_answer"]["word_target_min"], 20)
        self.assertEqual(type_map["long_answer"]["word_hard_max"], 220)

    def test_fill_in_blank_pending_review_then_examiner_accepts(self):
        exam_id, question_ids = self._create_exam_with_questions(
            [
                QuestionCreatePayload(
                    text="MS Access reports ka use ______ ke liye hota hai.",
                    topic="ms-access",
                    difficulty="easy",
                    marks=2,
                    question_type="fib_text",
                    accepted_answers=["data print karne ke liye"],
                )
            ]
        )
        question_id = question_ids[0]
        started = self._start_attempt(exam_id, "cadet-fib")
        attempt_id = started["attempt_id"]
        answer_text = "data summarize karne ke liye"

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            submit = delivery.submit_answer(
                AnswerSubmissionPayload(
                    attempt_id=attempt_id,
                    question_id=question_id,
                    text_answer=answer_text,
                ),
                "cadet-fib",
            )
            finalize = delivery.finalize_attempt(attempt_id, "cadet-fib")
            review = ReviewService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
            )
            fib_queue = review.list_fib_review_queue(exam_id)

        self.assertEqual(submit["question_type"], "fib_text")
        self.assertEqual(finalize["grading"], "pending_review")
        self.assertEqual(finalize["pending_review_count"], 1)
        self.assertIsNone(finalize["result"])
        self.assertEqual(len(fib_queue), 1)
        self.assertEqual(fib_queue[0]["question_id"], question_id)

        normalized = QuestionService.normalize_text_answer(answer_text)
        with UnitOfWork(self.db) as uow:
            review = ReviewService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
            )
            decision = review.apply_fib_decision(
                exam_id=exam_id,
                question_id=question_id,
                normalized_text_answer=normalized,
                decision="accepted",
                canonical_answer_text=answer_text,
                reviewer_id="examiner-1",
            )
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            result = delivery.get_result(attempt_id, "cadet-fib")

        self.assertEqual(decision["impacted_attempt_count"], 1)
        self.assertEqual(result["total_score"], 2.0)
        self.assertEqual(result["question_results"][0]["status"], "correct")

    def test_subjective_manual_scoring_creates_final_result(self):
        exam_id, question_ids = self._create_exam_with_questions(
            [
                QuestionCreatePayload(
                    text="What is a database management system?",
                    topic="databases",
                    difficulty="medium",
                    marks=4,
                    question_type="short_answer",
                    word_target_min=20,
                    word_target_max=50,
                    word_hard_max=80,
                )
            ]
        )
        question_id = question_ids[0]
        started = self._start_attempt(exam_id, "cadet-subjective")
        attempt_id = started["attempt_id"]
        answer_text = (
            "A database management system stores, organizes, and retrieves data "
            "through structured tables, queries, and controlled access rules."
        )

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
                    text_answer=answer_text,
                ),
                "cadet-subjective",
            )
            finalize = delivery.finalize_attempt(attempt_id, "cadet-subjective")
            review = ReviewService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
            )
            queue = review.list_subjective_review_queue(exam_id)

        self.assertEqual(finalize["grading"], "pending_review")
        self.assertEqual(finalize["pending_review_count"], 1)
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["question_type"], "short_answer")

        with UnitOfWork(self.db) as uow:
            review = ReviewService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
            )
            score = review.score_subjective_answer(
                attempt_id=attempt_id,
                question_id=question_id,
                marks_awarded=3.5,
                reviewer_id="examiner-2",
                review_note="Concepts covered well.",
            )
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            result = delivery.get_result(attempt_id, "cadet-subjective")

        self.assertTrue(score["result_ready"])
        self.assertEqual(result["total_score"], 3.5)
        self.assertEqual(result["question_results"][0]["marks_awarded"], 3.5)

    def test_true_false_auto_grades_without_negative_marking_and_short_answer_hard_limit(self):
        exam_id, question_ids = self._create_exam_with_questions(
            [
                QuestionCreatePayload(
                    text="SQLite WAL improves concurrent read access.",
                    topic="databases",
                    difficulty="easy",
                    marks=1,
                    question_type="true_false",
                    options=[("True", True)],
                ),
                QuestionCreatePayload(
                    text="What is a database management system?",
                    topic="databases",
                    difficulty="medium",
                    marks=4,
                    question_type="short_answer",
                    word_target_min=5,
                    word_target_max=10,
                    word_hard_max=12,
                ),
            ],
            negative_marking=0.25,
        )
        true_false_id, short_id = question_ids
        started = self._start_attempt(exam_id, "cadet-boolean")
        attempt_id = started["attempt_id"]

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            first_question = next(
                payload
                for payload in (
                    delivery.fetch_question(attempt_id, 1, "cadet-boolean"),
                    delivery.fetch_question(attempt_id, 2, "cadet-boolean"),
                )
                if payload["question"]["id"] == true_false_id
            )
            false_option = next(
                option
                for option in first_question["options"]
                if option["option_text"] == "False"
            )
            delivery.submit_answer(
                AnswerSubmissionPayload(
                    attempt_id=attempt_id,
                    question_id=true_false_id,
                    selected_option_id=false_option["id"],
                ),
                "cadet-boolean",
            )

            too_long = "one two three four five six seven eight nine ten eleven twelve thirteen"
            with self.assertRaises(DeliveryError):
                delivery.submit_answer(
                    AnswerSubmissionPayload(
                        attempt_id=attempt_id,
                        question_id=short_id,
                        text_answer=too_long,
                    ),
                    "cadet-boolean",
                )

            finalize = delivery.finalize_attempt(attempt_id, "cadet-boolean")
            result = delivery.get_result(attempt_id, "cadet-boolean")

        true_false_result = next(
            item
            for item in result["question_results"]
            if item["question_id"] == true_false_id
        )
        self.assertEqual(finalize["grading"], "completed")
        self.assertEqual(result["total_score"], 0.0)
        self.assertEqual(true_false_result["status"], "incorrect")
        self.assertEqual(true_false_result["marks_awarded"], 0.0)


if __name__ == "__main__":
    unittest.main()
