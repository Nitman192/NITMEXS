import tempfile
import unittest
from pathlib import Path

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import DeliveryService
from phase1_server.services.exam_service import ExamCreatePayload, ExamService
from phase1_server.services.proctor_alert_service import (
    ProctorAlertService,
    ProctorAlertValidationError,
)
from phase1_server.services.proctoring_service import ProctoringService
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


class ProctorAlertTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "proctor_alerts.db")
        self.db = Database(SQLiteConfig(db_path=self.db_path))
        self.db.initialize()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _seed_exam(self) -> str:
        with UnitOfWork(self.db) as uow:
            q_service = QuestionService(uow.questions)
            question = q_service.create_question(
                QuestionCreatePayload(
                    text="Alert seed question",
                    topic="proctoring",
                    difficulty="easy",
                    marks=2.0,
                    options=[("A", True), ("B", False)],
                )
            )
            exam_service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
            exam = exam_service.create_exam(
                ExamCreatePayload(
                    name="Proctor Alert Exam",
                    duration_minutes=30,
                    negative_marking=0.0,
                )
            )
            exam_service.add_questions(exam.id, [question.id])
            exam_service.publish_exam(exam.id)
            return exam.id

    def _start_expired_active_attempt(self, exam_id: str, student_id: str) -> str:
        with UnitOfWork(self.db) as uow:
            delivery = DeliveryService(
                uow.attempts,
                uow.exams,
                uow.questions,
                audit_service=AuditService(uow.audit_events),
            )
            started = delivery.start_attempt(exam_id=exam_id, student_id=student_id)
            uow.conn.execute(
                "UPDATE attempts SET expires_at = ? WHERE id = ?",
                ("2000-01-01T00:00:00+00:00", started["attempt_id"]),
            )
            return started["attempt_id"]

    def test_alert_sync_is_idempotent_and_supports_acknowledge_resolve(self):
        exam_id = self._seed_exam()
        attempt_id = self._start_expired_active_attempt(exam_id, "alert-student")

        with UnitOfWork(self.db) as uow:
            service = ProctorAlertService(
                alert_repo=uow.proctor_alerts,
                exam_repo=uow.exams,
                proctoring_service=ProctoringService(uow.attempts, uow.exams),
                audit_service=AuditService(uow.audit_events),
            )
            first_sync = service.sync_alerts(exam_id=exam_id, triggered_by="admin-sync")
            second_sync = service.sync_alerts(exam_id=exam_id, triggered_by="admin-sync")
            summary = service.get_alert_summary(exam_id=exam_id)
            live_alerts = service.get_live_alerts(exam_id=exam_id, limit=100)

            self.assertGreaterEqual(first_sync["created_count"], 1)
            self.assertEqual(second_sync["created_count"], 0)
            self.assertGreaterEqual(second_sync["updated_count"], 1)
            self.assertGreaterEqual(summary["summary"]["open_count"], 1)
            self.assertGreaterEqual(len(summary["summary"]["by_indicator"]), 1)
            self.assertGreaterEqual(live_alerts["count"], 1)
            self.assertTrue(
                all(
                    item["status"] in {"open", "acknowledged"}
                    for item in live_alerts["alerts"]
                )
            )

            open_alerts = service.list_alerts(exam_id=exam_id, status="open")
            self.assertGreaterEqual(open_alerts["count"], 1)
            alert_id = open_alerts["alerts"][0]["id"]
            acknowledged_once = service.acknowledge_alert(alert_id, actor_id="invigilator-1")
            acknowledged_twice = service.acknowledge_alert(alert_id, actor_id="invigilator-1")
            resolved_once = service.resolve_alert(
                alert_id,
                actor_id="invigilator-1",
                note="reviewed",
            )
            resolved_twice = service.resolve_alert(
                alert_id,
                actor_id="invigilator-1",
                note="reviewed",
            )
            with self.assertRaises(ProctorAlertValidationError):
                service.acknowledge_alert(alert_id, actor_id="invigilator-1")

            uow.conn.execute(
                "UPDATE attempts SET status = 'finalized' WHERE id = ?",
                (attempt_id,),
            )
            third_sync = service.sync_alerts(exam_id=exam_id, triggered_by="admin-sync")
            self.assertGreaterEqual(third_sync["auto_resolved_count"], 1)

            unresolved_after_auto = service.get_live_alerts(exam_id=exam_id, limit=100)
            timeline = AuditService(uow.audit_events).list_entity_timeline(
                "attempt",
                attempt_id,
            )
            metrics_view = service.get_operational_metrics(
                exam_id=exam_id,
                stale_after_minutes=1,
            )

        self.assertTrue(acknowledged_once["changed"])
        self.assertFalse(acknowledged_twice["changed"])
        self.assertTrue(resolved_once["changed"])
        self.assertFalse(resolved_twice["changed"])
        self.assertEqual(unresolved_after_auto["count"], 0)
        self.assertEqual(resolved_once["alert"]["status"], "resolved")
        self.assertEqual(metrics_view["kpis"]["unresolved_count"], 0)
        self.assertGreaterEqual(metrics_view["summary"]["resolved_count"], 1)
        event_types = [event["event_type"] for event in timeline]
        self.assertIn("PROCTOR_ALERT_RAISED", event_types)
        self.assertIn("PROCTOR_ALERT_ACKNOWLEDGED", event_types)
        self.assertIn("PROCTOR_ALERT_AUTO_RESOLVED", event_types)
        self.assertIn("PROCTOR_ALERT_RESOLVED", event_types)

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
    def test_admin_proctor_alert_endpoints(self):
        exam_id = self._seed_exam()
        self._start_expired_active_attempt(exam_id, "api-alert-student")

        app = create_app(db_path=self.db_path)
        with TestClient(app) as client:
            headers = {"x-admin": "true", "x-admin-id": "api-admin"}
            sync_response = client.post(
                f"/admin/proctor/alerts/sync?exam_id={exam_id}&active_limit=100",
                headers=headers,
            )
            open_response = client.get(
                f"/admin/proctor/alerts?exam_id={exam_id}&status=open&limit=100",
                headers=headers,
            )
            summary_response = client.get(
                f"/admin/proctor/alerts/summary?exam_id={exam_id}",
                headers=headers,
            )
            metrics_response = client.get(
                f"/admin/proctor/alerts/metrics?exam_id={exam_id}&stale_after_minutes=1",
                headers=headers,
            )
            live_response = client.get(
                f"/admin/exams/{exam_id}/proctor-alerts/live?limit=100",
                headers=headers,
            )
            alert_id = open_response.json()["data"]["alerts"][0]["id"]
            ack_response = client.post(
                f"/admin/proctor/alerts/{alert_id}/acknowledge",
                headers=headers,
            )
            resolve_response = client.post(
                f"/admin/proctor/alerts/{alert_id}/resolve",
                headers=headers,
                json={"note": "manually verified"},
            )
            resolved_response = client.get(
                f"/admin/proctor/alerts?exam_id={exam_id}&status=resolved&limit=100",
                headers=headers,
            )
            invalid_status = client.get(
                "/admin/proctor/alerts?status=invalid",
                headers=headers,
            )
            system_metrics = client.get(
                "/admin/system/metrics",
                headers=headers,
            )
            missing_alert = client.post(
                "/admin/proctor/alerts/does-not-exist/acknowledge",
                headers=headers,
            )

        self.assertEqual(sync_response.status_code, 200)
        self.assertEqual(open_response.status_code, 200)
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(metrics_response.status_code, 200)
        self.assertEqual(live_response.status_code, 200)
        self.assertEqual(ack_response.status_code, 200)
        self.assertEqual(resolve_response.status_code, 200)
        self.assertEqual(resolved_response.status_code, 200)
        self.assertEqual(invalid_status.status_code, 400)
        self.assertEqual(system_metrics.status_code, 200)
        self.assertEqual(missing_alert.status_code, 404)
        self.assertEqual(sync_response.json()["status"], "success")
        self.assertGreaterEqual(summary_response.json()["data"]["summary"]["total_count"], 1)
        self.assertIn("kpis", metrics_response.json()["data"])
        self.assertGreaterEqual(live_response.json()["data"]["count"], 1)
        self.assertEqual(resolve_response.json()["data"]["alert"]["status"], "resolved")
        self.assertGreaterEqual(resolved_response.json()["data"]["count"], 1)
        metrics_payload = system_metrics.json()["data"]
        self.assertIn("proctor_alert_raised_count", metrics_payload)
        self.assertIn("proctor_alert_acknowledged_count", metrics_payload)
        self.assertIn("proctor_alert_resolved_count", metrics_payload)


if __name__ == "__main__":
    unittest.main()
