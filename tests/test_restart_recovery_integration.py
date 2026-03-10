import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

try:
    import httpx
    HTTPX_AVAILABLE = True
except Exception:
    httpx = None
    HTTPX_AVAILABLE = False

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.exam_service import ExamCreatePayload, ExamService
from phase1_server.services.question_service import QuestionCreatePayload, QuestionService
from phase1_server.uow import UnitOfWork


def wait_ready(base_url: str, timeout_s: float = 15.0) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            response = httpx.get(f"{base_url}/system/version", timeout=2.0)
            if response.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError("Server not ready")


@unittest.skipUnless(HTTPX_AVAILABLE, "httpx unavailable")
class RestartRecoveryIntegrationTests(unittest.TestCase):
    def _seed_exam(self, db_path: str) -> str:
        db = Database(SQLiteConfig(db_path=db_path))
        db.initialize()
        with UnitOfWork(db) as uow:
            q_service = QuestionService(uow.questions)
            qids = []
            for i in range(2):
                q = q_service.create_question(
                    QuestionCreatePayload(
                        text=f"Recovery Q{i}",
                        topic="ops",
                        difficulty="easy",
                        marks=1,
                        options=[("A", True), ("B", False)],
                    )
                )
                qids.append(q.id)

            e_service = ExamService(uow.exams, uow.questions)
            exam = e_service.create_exam(
                ExamCreatePayload(name="Recovery Exam", duration_minutes=20, negative_marking=0)
            )
            e_service.add_questions(exam.id, qids)
            e_service.publish_exam(exam.id)
            return exam.id

    def test_snapshot_attempt_and_audit_persist_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "restart.db")
            exam_id = self._seed_exam(db_path)

            env = os.environ.copy()
            env["NITMEXS_DB_PATH"] = db_path
            env["NITMEXS_HOST"] = "127.0.0.1"
            env["NITMEXS_PORT"] = "8000"

            server = subprocess.Popen(
                [sys.executable, "-m", "phase1_server.server_entry", "--mode", "foreground"],
                env=env,
            )
            try:
                wait_ready("http://127.0.0.1:8000")

                start = httpx.post(
                    f"http://127.0.0.1:8000/student/exams/{exam_id}/start",
                    headers={"x-student-id": "recover-student"},
                    timeout=10.0,
                )
                self.assertEqual(start.status_code, 200)
                attempt_id = start.json()["data"]["attempt_id"]

                q1 = httpx.get(
                    f"http://127.0.0.1:8000/student/attempts/{attempt_id}/questions/1",
                    headers={"x-student-id": "recover-student"},
                    timeout=10.0,
                )
                self.assertEqual(q1.status_code, 200)
                q1_payload = q1.json()["data"]
                submit = httpx.post(
                    f"http://127.0.0.1:8000/student/attempts/{attempt_id}/answers",
                    headers={"x-student-id": "recover-student"},
                    json={
                        "question_id": q1_payload["question"]["id"],
                        "selected_option_id": q1_payload["options"][0]["id"],
                    },
                    timeout=10.0,
                )
                self.assertEqual(submit.status_code, 200)
            finally:
                server.terminate()
                try:
                    server.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()

            server2 = subprocess.Popen(
                [sys.executable, "-m", "phase1_server.server_entry", "--mode", "foreground"],
                env=env,
            )
            try:
                wait_ready("http://127.0.0.1:8000")

                # Snapshot persistence
                q1_after = httpx.get(
                    f"http://127.0.0.1:8000/student/attempts/{attempt_id}/questions/1",
                    headers={"x-student-id": "recover-student"},
                    timeout=10.0,
                )
                self.assertEqual(q1_after.status_code, 200)

                # Attempt state preserved (still active)
                q2_after = httpx.get(
                    f"http://127.0.0.1:8000/student/attempts/{attempt_id}/questions/2",
                    headers={"x-student-id": "recover-student"},
                    timeout=10.0,
                )
                self.assertEqual(q2_after.status_code, 200)

                # Audit events preserved
                timeline = httpx.get(
                    f"http://127.0.0.1:8000/admin/attempts/{attempt_id}/timeline",
                    headers={"x-admin": "true"},
                    timeout=10.0,
                )
                self.assertEqual(timeline.status_code, 200)
                events = timeline.json()["data"]
                event_types = [event["event_type"] for event in events]
                self.assertIn("ATTEMPT_STARTED", event_types)
                self.assertIn("ANSWER_SUBMITTED", event_types)
            finally:
                server2.terminate()
                try:
                    server2.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server2.kill()


if __name__ == "__main__":
    unittest.main()
