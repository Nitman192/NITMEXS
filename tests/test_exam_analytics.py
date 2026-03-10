import tempfile
import unittest

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.analytics_service import AnalyticsService
from phase1_server.services.delivery_service import (
    AnswerSubmissionPayload,
    DeliveryService,
)
from phase1_server.services.exam_service import (
    ExamCreatePayload,
    ExamNotFoundError,
    ExamService,
)
from phase1_server.services.question_service import QuestionCreatePayload, QuestionService
from phase1_server.uow import UnitOfWork


class ExamAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db")
        self.db = Database(SQLiteConfig(db_path=self.tmp.name))
        self.db.initialize()

    def tearDown(self):
        self.tmp.close()

    def _seed_exam(self) -> tuple[str, list[str]]:
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
                    name="Analytics Exam",
                    duration_minutes=30,
                    negative_marking=0,
                )
            )
            e_service.add_questions(exam.id, question_ids)
            e_service.publish_exam(exam.id)

        return exam.id, question_ids

    def _complete_attempt(self, exam_id: str, student_id: str, all_correct: bool) -> None:
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                analytics_repo=uow.analytics,
            )
            started = service.start_attempt(exam_id, student_id)
            for sequence in (1, 2, 3):
                question_payload = service.fetch_question(
                    started["attempt_id"], sequence, student_id
                )
                if all_correct:
                    selected = next(
                        option
                        for option in question_payload["options"]
                        if option["option_text"].startswith("A")
                    )
                else:
                    selected = next(
                        option
                        for option in question_payload["options"]
                        if not option["option_text"].startswith("A")
                    )
                service.submit_answer(
                    AnswerSubmissionPayload(
                        attempt_id=started["attempt_id"],
                        question_id=question_payload["question"]["id"],
                        selected_option_id=selected["id"],
                    ),
                    student_id,
                )
            service.finalize_attempt(started["attempt_id"], student_id)

    def test_difficulty_index_and_pass_rate(self):
        exam_id, _ = self._seed_exam()
        self._complete_attempt(exam_id, "stu1", all_correct=True)
        self._complete_attempt(exam_id, "stu2", all_correct=False)

        with UnitOfWork(self.db) as uow:
            service = AnalyticsService(uow.analytics, uow.exams)
            result = service.get_exam_analytics(exam_id)

        self.assertEqual(result["exam_id"], exam_id)
        self.assertEqual(len(result["question_metrics"]), 3)

        for metric in result["question_metrics"]:
            self.assertEqual(metric["total_attempts"], 2)
            self.assertAlmostEqual(metric["difficulty_index"], 50.0)
            self.assertAlmostEqual(metric["average_score"], 1.0)

        summary = result["summary"]
        self.assertAlmostEqual(summary["mean_score"], 3.0)
        self.assertAlmostEqual(summary["pass_rate"], 50.0)
        self.assertEqual(summary["total_attempts"], 2)

    def test_student_performance_aggregation(self):
        exam_id1, _ = self._seed_exam()
        exam_id2, _ = self._seed_exam()
        self._complete_attempt(exam_id1, "stu1", all_correct=True)
        self._complete_attempt(exam_id2, "stu1", all_correct=False)

        with UnitOfWork(self.db) as uow:
            service = AnalyticsService(uow.analytics, uow.exams)
            data = service.get_student_performance("stu1")

        self.assertEqual(data["student_id"], "stu1")
        self.assertEqual(data["total_attempts"], 2)
        self.assertEqual(data["passed_attempts"], 1)
        self.assertAlmostEqual(data["pass_rate"], 50.0)
        self.assertEqual(len(data["attempts"]), 2)

    def test_service_raises_for_missing_exam(self):
        with UnitOfWork(self.db) as uow:
            service = AnalyticsService(uow.analytics, uow.exams)
            with self.assertRaises(ExamNotFoundError):
                service.get_exam_analytics("missing-exam")


if __name__ == "__main__":
    unittest.main()
