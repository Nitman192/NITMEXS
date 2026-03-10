import tempfile
import unittest
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.analytics_service import AnalyticsService
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import (
    AnswerSubmissionPayload,
    DeliveryService,
)
from phase1_server.services.exam_service import ExamCreatePayload, ExamService
from phase1_server.services.proctoring_service import ProctoringService
from phase1_server.services.question_service import (
    QuestionCreatePayload,
    QuestionMetadataUpdatePayload,
    QuestionService,
)
from phase1_server.uow import UnitOfWork

try:
    from fastapi.testclient import TestClient
    from phase1_server.app import create_app

    FASTAPI_AVAILABLE = True
except Exception:
    TestClient = None
    create_app = None
    FASTAPI_AVAILABLE = False


class Phase2MonitoringAndMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "phase2.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _seed_exam(self, question_count: int = 3) -> tuple[str, list[str], int]:
        with UnitOfWork(self.db) as uow:
            q_service = QuestionService(uow.questions)
            question_ids: list[str] = []
            for idx in range(question_count):
                question = q_service.create_question(
                    QuestionCreatePayload(
                        text=f"Question {idx}",
                        topic=f"topic-{idx % 2}",
                        difficulty="easy",
                        marks=2.0,
                        difficulty_level=idx + 1,
                        discrimination_index=0.3,
                        topic_tag=f"tag-{idx % 2}",
                        cognitive_level="understand",
                        options=[
                            (f"A{idx}", True),
                            (f"B{idx}", False),
                            (f"C{idx}", False),
                        ],
                    )
                )
                question_ids.append(question.id)

            e_service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
            exam = e_service.create_exam(
                ExamCreatePayload(
                    name="Phase 2 Exam",
                    duration_minutes=30,
                    negative_marking=0.5,
                )
            )
            e_service.add_questions(exam.id, question_ids)
            e_service.publish_exam(exam.id)
        return exam.id, question_ids, question_count

    def _complete_attempt(
        self,
        exam_id: str,
        student_id: str,
        question_count: int,
        all_correct: bool,
    ) -> str:
        with UnitOfWork(self.db) as uow:
            service = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                analytics_repo=uow.analytics,
                audit_service=AuditService(uow.audit_events),
            )
            started = service.start_attempt(exam_id=exam_id, student_id=student_id)
            for sequence in range(1, question_count + 1):
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
                    student_id=student_id,
                )

            service.finalize_attempt(started["attempt_id"], student_id)
            return started["attempt_id"]

    def test_question_metadata_defaults_and_update(self):
        with UnitOfWork(self.db) as uow:
            service = QuestionService(uow.questions)
            question = service.create_question(
                QuestionCreatePayload(
                    text="Metadata question",
                    topic="networking",
                    difficulty="medium",
                    marks=2.0,
                    options=[("A", True), ("B", False)],
                )
            )
            listed = service.list_questions()
            listed_item = next(item for item in listed if item["id"] == question.id)
            self.assertEqual(listed_item["topic_tag"], "networking")

            updated = service.update_question_metadata(
                question.id,
                QuestionMetadataUpdatePayload(
                    difficulty_level=7,
                    discrimination_index=0.72,
                    topic_tag="lan-core",
                    cognitive_level="analyze",
                ),
            )

        self.assertEqual(updated.difficulty_level, 7)
        self.assertAlmostEqual(updated.discrimination_index, 0.72)
        self.assertEqual(updated.topic_tag, "lan-core")
        self.assertEqual(updated.cognitive_level, "analyze")

    def test_question_usage_stats_after_grading(self):
        exam_id, question_ids, _ = self._seed_exam(question_count=1)

        with UnitOfWork(self.db) as uow:
            service = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            started = service.start_attempt(exam_id, "usage-student")
            first_question = service.fetch_question(started["attempt_id"], 1, "usage-student")
            correct_option = next(
                option for option in first_question["options"] if option["option_text"].startswith("A")
            )
            service.submit_answer(
                AnswerSubmissionPayload(
                    attempt_id=started["attempt_id"],
                    question_id=first_question["question"]["id"],
                    selected_option_id=correct_option["id"],
                ),
                "usage-student",
            )
            service.finalize_attempt(started["attempt_id"], "usage-student")

            stats = QuestionService(uow.questions).get_question_usage_statistics()
            row = next(item for item in stats if item["question_id"] == question_ids[0])

        self.assertEqual(row["usage_count"], 1)
        self.assertEqual(row["correct_count"], 1)
        self.assertAlmostEqual(row["correct_rate"], 100.0)

    def test_proctoring_active_attempts_and_live_status(self):
        exam_id, _, _ = self._seed_exam(question_count=3)
        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            started = delivery.start_attempt(exam_id, "monitor-student")
            first_question = delivery.fetch_question(started["attempt_id"], 1, "monitor-student")
            selected = first_question["options"][0]["id"]
            delivery.submit_answer(
                AnswerSubmissionPayload(
                    attempt_id=started["attempt_id"],
                    question_id=first_question["question"]["id"],
                    selected_option_id=selected,
                ),
                "monitor-student",
            )

            proctor = ProctoringService(uow.attempts, uow.exams)
            active_attempts = proctor.get_active_attempts(exam_id)
            live_status = proctor.get_live_status(exam_id)

        self.assertEqual(len(active_attempts), 1)
        self.assertEqual(active_attempts[0]["student_id"], "monitor-student")
        self.assertEqual(active_attempts[0]["answered_question_count"], 1)
        self.assertGreaterEqual(active_attempts[0]["remaining_seconds"], 0)
        self.assertEqual(live_status["active_attempt_count"], 1)

    def test_live_status_includes_finalize_events(self):
        exam_id, _, _ = self._seed_exam(question_count=1)
        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            started = delivery.start_attempt(exam_id, "finalize-student")
            delivery.finalize_attempt(started["attempt_id"], "finalize-student")

            live_status = ProctoringService(uow.attempts, uow.exams).get_live_status(exam_id)

        self.assertTrue(
            any(
                event["attempt_id"] == started["attempt_id"]
                for event in live_status["recent_finalize_events"]
            )
        )

    def test_proctor_dashboard_aggregates_across_exams(self):
        exam_id_1, _, _ = self._seed_exam(question_count=2)
        exam_id_2, _, _ = self._seed_exam(question_count=2)

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            active_one = delivery.start_attempt(exam_id_1, "dash-active-1")
            active_two = delivery.start_attempt(exam_id_2, "dash-active-2")
            finalized = delivery.start_attempt(exam_id_1, "dash-finalized")
            delivery.finalize_attempt(finalized["attempt_id"], "dash-finalized")

            dashboard = ProctoringService(uow.attempts, uow.exams).get_dashboard(
                active_limit=100,
                finalize_limit=20,
            )

        self.assertEqual(dashboard["active_attempt_count"], 2)
        self.assertEqual(
            sorted(item["exam_id"] for item in dashboard["active_attempts"]),
            sorted([exam_id_1, exam_id_2]),
        )
        self.assertTrue(
            any(
                event["attempt_id"] == finalized["attempt_id"]
                for event in dashboard["recent_finalize_events"]
            )
        )
        summary_map = {item["exam_id"]: item for item in dashboard["exam_summaries"]}
        self.assertIn(exam_id_1, summary_map)
        self.assertIn(exam_id_2, summary_map)
        self.assertEqual(summary_map[exam_id_1]["active_attempt_count"], 1)
        self.assertEqual(summary_map[exam_id_2]["active_attempt_count"], 1)
        self.assertEqual(active_one["status"], "active")
        self.assertEqual(active_two["status"], "active")

    def test_proctor_event_stream_filters_and_since_cursor(self):
        exam_id_1, _, _ = self._seed_exam(question_count=1)
        exam_id_2, _, _ = self._seed_exam(question_count=1)

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            first = delivery.start_attempt(exam_id_1, "evt-student-1")
            delivery.start_attempt(exam_id_2, "evt-student-2")
            delivery.finalize_attempt(first["attempt_id"], "evt-student-1")

            proctor = ProctoringService(uow.attempts, uow.exams)
            all_events = proctor.get_event_stream(limit=200)
            self.assertGreaterEqual(all_events["count"], 3)
            first_cursor = all_events["events"][0]["created_at"]

            since_events = proctor.get_event_stream(limit=200, since=first_cursor)
            self.assertTrue(
                all(event["created_at"] > first_cursor for event in since_events["events"])
            )

            exam_events = proctor.get_event_stream(limit=200, exam_id=exam_id_1)
            self.assertTrue(all(event["exam_id"] == exam_id_1 for event in exam_events["events"]))
            self.assertTrue(any(event["event_type"] == "FINALIZED" for event in exam_events["events"]))

            first_page = proctor.get_event_stream(limit=1, exam_id=exam_id_1)
            cursor_token = first_page["next_cursor"]
            second_page = proctor.get_event_stream(
                limit=200,
                exam_id=exam_id_1,
                cursor=cursor_token,
            )
            first_ids = {event["event_id"] for event in first_page["events"]}
            second_ids = {event["event_id"] for event in second_page["events"]}
            self.assertTrue(first_ids.isdisjoint(second_ids))

    def test_proctor_event_stream_cursor_handles_same_timestamp_boundary(self):
        exam_id, _, _ = self._seed_exam(question_count=1)
        fixed_ts = "2030-01-01T00:00:00+00:00"

        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
                analytics_repo=uow.analytics,
            )
            started = delivery.start_attempt(exam_id, "cursor-same-ts")

            audit = AuditService(uow.audit_events)
            audit.log_event(
                entity_type="attempt",
                entity_id=started["attempt_id"],
                actor_type="system",
                actor_id="system",
                event_type="CURSOR_TEST_A",
                payload={"marker": "a"},
                created_at=fixed_ts,
            )
            audit.log_event(
                entity_type="attempt",
                entity_id=started["attempt_id"],
                actor_type="system",
                actor_id="system",
                event_type="CURSOR_TEST_B",
                payload={"marker": "b"},
                created_at=fixed_ts,
            )

            proctor = ProctoringService(uow.attempts, uow.exams)
            all_events = proctor.get_event_stream(limit=500, exam_id=exam_id)["events"]
            same_ts_events = [
                event for event in all_events if event["created_at"] == fixed_ts
            ]
            self.assertEqual(len(same_ts_events), 2)

            first_same_ts_id = same_ts_events[0]["event_id"]
            second_same_ts_id = same_ts_events[1]["event_id"]
            first_index = next(
                idx for idx, event in enumerate(all_events) if event["event_id"] == first_same_ts_id
            )

            page_one = proctor.get_event_stream(
                limit=first_index + 1,
                exam_id=exam_id,
            )
            page_two = proctor.get_event_stream(
                limit=500,
                exam_id=exam_id,
                cursor=page_one["next_cursor"],
            )
            page_two_ids = [event["event_id"] for event in page_two["events"]]

        self.assertIn(second_same_ts_id, page_two_ids)
        self.assertNotIn(first_same_ts_id, page_two_ids)

    def test_analytics_visualization_payloads(self):
        exam_id, _, question_count = self._seed_exam(question_count=3)
        self._complete_attempt(
            exam_id=exam_id,
            student_id="analytics-a",
            question_count=question_count,
            all_correct=True,
        )
        self._complete_attempt(
            exam_id=exam_id,
            student_id="analytics-b",
            question_count=question_count,
            all_correct=False,
        )

        with UnitOfWork(self.db) as uow:
            service = AnalyticsService(uow.analytics, uow.exams)
            difficulty_heatmap = service.get_question_difficulty_heatmap(exam_id)
            topic_heatmap = service.get_topic_performance_heatmap(exam_id)
            score_distribution = service.get_score_distribution(exam_id)

        self.assertEqual(difficulty_heatmap["exam_id"], exam_id)
        self.assertEqual(len(difficulty_heatmap["cells"]), question_count)
        self.assertEqual(topic_heatmap["exam_id"], exam_id)
        self.assertGreaterEqual(len(topic_heatmap["cells"]), 1)
        self.assertEqual(score_distribution["exam_id"], exam_id)
        self.assertEqual(score_distribution["total_attempts"], 2)
        self.assertEqual(
            sum(bucket["count"] for bucket in score_distribution["buckets"]),
            2,
        )

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
    def test_admin_endpoints_for_live_status_and_analytics(self):
        exam_id, _, _ = self._seed_exam(question_count=2)
        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
            )
            delivery.start_attempt(exam_id, "api-monitor")

        app = create_app(db_path=self.db_path)
        with TestClient(app) as client:
            headers = {"x-admin": "true"}
            active = client.get(f"/admin/exams/{exam_id}/active-attempts", headers=headers)
            live = client.get(f"/admin/exams/{exam_id}/live-status", headers=headers)
            heat = client.get(
                f"/admin/exams/{exam_id}/analytics/difficulty-heatmap",
                headers=headers,
            )
            topic = client.get(
                f"/admin/exams/{exam_id}/analytics/topic-heatmap",
                headers=headers,
            )
            distribution = client.get(
                f"/admin/exams/{exam_id}/analytics/score-distribution",
                headers=headers,
            )
            dashboard = client.get(
                "/admin/proctor/dashboard?active_limit=100&finalize_limit=20",
                headers=headers,
            )
            events = client.get(
                "/admin/proctor/events?limit=100",
                headers=headers,
            )
            cursor_page = client.get(
                "/admin/proctor/events?limit=1",
                headers=headers,
            )
            next_cursor = cursor_page.json()["data"]["next_cursor"]
            events_next = client.get(
                f"/admin/proctor/events?limit=100&cursor={next_cursor}",
                headers=headers,
            )
            events_invalid_since = client.get(
                "/admin/proctor/events?since=not-a-date",
                headers=headers,
            )
            events_invalid_cursor = client.get(
                "/admin/proctor/events?cursor=not-a-cursor",
                headers=headers,
            )
            events_cursor_and_since = client.get(
                "/admin/proctor/events?cursor=abc&since=2026-01-01T00:00:00+00:00",
                headers=headers,
            )

        self.assertEqual(active.status_code, 200)
        self.assertEqual(live.status_code, 200)
        self.assertEqual(heat.status_code, 200)
        self.assertEqual(topic.status_code, 200)
        self.assertEqual(distribution.status_code, 200)
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(events.status_code, 200)
        self.assertEqual(events_next.status_code, 200)
        self.assertEqual(events_invalid_since.status_code, 400)
        self.assertEqual(events_invalid_cursor.status_code, 400)
        self.assertEqual(events_cursor_and_since.status_code, 400)
        self.assertEqual(active.json()["status"], "success")
        self.assertEqual(live.json()["status"], "success")
        self.assertEqual(dashboard.json()["status"], "success")
        self.assertEqual(events.json()["status"], "success")
        self.assertIn("exam_summaries", dashboard.json()["data"])
        self.assertIn("events", events.json()["data"])


if __name__ == "__main__":
    unittest.main()
