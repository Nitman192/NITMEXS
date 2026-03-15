import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from phase1_server.app import create_app


class AuthRulesAndTimerControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "auth_rules_timer.db")
        self.app = create_app(db_path=self.db_path)
        self.client = TestClient(self.app)
        self.superadmin_headers = {"x-admin": "true", "x-admin-id": "superadmin"}

    def tearDown(self):
        self.client.close()
        self.tmp_dir.cleanup()

    def _create_question(self, headers, text="What is DBMS?"):
        response = self.client.post(
            "/admin/questions",
            headers=headers,
            json={
                "text": text,
                "topic": "Database",
                "difficulty": "easy",
                "marks": 1,
                "question_type": "mcq_single",
                "options": [
                    {"option_text": "Database Management System", "is_correct": True},
                    {"option_text": "Data Business Machine Setup", "is_correct": False},
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["data"]["id"]

    def _create_exam(self, headers, name="Signals Exam"):
        response = self.client.post(
            "/admin/exams",
            headers=headers,
            json={"name": name, "duration_minutes": 30, "negative_marking": 0},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["data"]["id"]

    def test_student_login_requires_registered_password(self):
        create_response = self.client.post(
            "/admin/students/register",
            headers=self.superadmin_headers,
            json={
                "student_id": "cadet-login-1",
                "display_name": "Cadet Login",
                "password": "Secure@123",
            },
        )
        self.assertEqual(create_response.status_code, 201, create_response.text)

        wrong = self.client.post(
            "/student/login",
            json={"student_id": "cadet-login-1", "password": "wrong-pass"},
        )
        correct = self.client.post(
            "/student/login",
            json={"student_id": "cadet-login-1", "password": "Secure@123"},
        )

        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(correct.status_code, 200)
        self.assertEqual(correct.json()["data"]["student_id"], "cadet-login-1")

    def test_exam_rules_preview_includes_default_and_custom_rules(self):
        exam_id = self._create_exam(self.superadmin_headers, name="Rules Preview Exam")
        update_rules = self.client.patch(
            f"/admin/exams/{exam_id}/rules",
            headers=self.superadmin_headers,
            json={"custom_rules": ["Carry ID card.", "Maintain silence in the lab."]},
        )
        self.assertEqual(update_rules.status_code, 200, update_rules.text)

        preview = self.client.get(
            f"/student/exams/{exam_id}/rules-preview",
            headers={"x-student-id": "preview-student"},
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        rules = preview.json()["data"]["rules"]
        self.assertIn("Use Save & Next to persist each answer.", rules)
        self.assertIn("Carry ID card.", rules)
        self.assertIn("Maintain silence in the lab.", rules)

    def test_examiner_data_isolation_and_superadmin_visibility(self):
        for admin_id in ("examiner-1", "examiner-2"):
            response = self.client.post(
                "/admin/accounts",
                headers=self.superadmin_headers,
                json={
                    "admin_id": admin_id,
                    "display_name": admin_id.title(),
                    "role": "examiner",
                    "access_key": f"{admin_id}@123",
                },
            )
            self.assertEqual(response.status_code, 201, response.text)

        examiner_one_headers = {"x-admin": "true", "x-admin-id": "examiner-1"}
        examiner_two_headers = {"x-admin": "true", "x-admin-id": "examiner-2"}
        created_question_id = self._create_question(examiner_one_headers, text="Examiner one question")
        exam_id = self._create_exam(examiner_one_headers, name="Examiner One Exam")
        attach_response = self.client.post(
            f"/admin/exams/{exam_id}/add-questions",
            headers=examiner_one_headers,
            json={"question_ids": [created_question_id]},
        )
        self.assertEqual(attach_response.status_code, 200, attach_response.text)

        examiner_one_questions = self.client.get("/admin/questions", headers=examiner_one_headers)
        examiner_two_questions = self.client.get("/admin/questions", headers=examiner_two_headers)
        superadmin_questions = self.client.get("/admin/questions", headers=self.superadmin_headers)

        examiner_one_exams = self.client.get("/admin/exams", headers=examiner_one_headers)
        examiner_two_exams = self.client.get("/admin/exams", headers=examiner_two_headers)
        superadmin_exams = self.client.get("/admin/exams", headers=self.superadmin_headers)

        self.assertEqual(examiner_one_questions.status_code, 200)
        self.assertEqual(examiner_two_questions.status_code, 200)
        self.assertEqual(superadmin_questions.status_code, 200)
        self.assertEqual(len(examiner_one_questions.json()["data"]), 1)
        self.assertEqual(len(examiner_two_questions.json()["data"]), 0)
        self.assertEqual(len(superadmin_questions.json()["data"]), 1)

        self.assertEqual(len(examiner_one_exams.json()["data"]), 1)
        self.assertEqual(len(examiner_two_exams.json()["data"]), 0)
        self.assertEqual(len(superadmin_exams.json()["data"]), 1)

    def test_pause_with_freeze_timer_extends_exam_expiry(self):
        self.client.post(
            "/admin/students/register",
            headers=self.superadmin_headers,
            json={
                "student_id": "cadet-freeze-1",
                "display_name": "Cadet Freeze",
                "password": "Freeze@123",
            },
        )
        question_id = self._create_question(self.superadmin_headers, text="Freeze timer question")
        exam_id = self._create_exam(self.superadmin_headers, name="Freeze Timer Exam")
        self.client.post(
            f"/admin/exams/{exam_id}/add-questions",
            headers=self.superadmin_headers,
            json={"question_ids": [question_id]},
        )
        publish = self.client.post(f"/admin/exams/{exam_id}/publish", headers=self.superadmin_headers)
        self.assertEqual(publish.status_code, 200, publish.text)

        start = self.client.post(
            f"/student/exams/{exam_id}/start",
            headers={"x-student-id": "cadet-freeze-1"},
        )
        self.assertEqual(start.status_code, 200, start.text)
        data = start.json()["data"]
        attempt_id = data["attempt_id"]
        original_expires_at = data["expires_at"]

        pause = self.client.post(
            f"/admin/exams/{exam_id}/pause",
            headers=self.superadmin_headers,
            json={"reason": "Emergency hold", "freeze_timer": True},
        )
        self.assertEqual(pause.status_code, 200, pause.text)
        paused_status = self.client.get(
            f"/student/attempts/{attempt_id}/status",
            headers={"x-student-id": "cadet-freeze-1"},
        )
        self.assertEqual(paused_status.status_code, 200, paused_status.text)
        self.assertTrue(paused_status.json()["data"]["timer_frozen"])

        time.sleep(1.2)

        resume = self.client.post(
            f"/admin/exams/{exam_id}/resume",
            headers=self.superadmin_headers,
            json={"reason": "Resume after hold"},
        )
        self.assertEqual(resume.status_code, 200, resume.text)
        resumed_status = self.client.get(
            f"/student/attempts/{attempt_id}/status",
            headers={"x-student-id": "cadet-freeze-1"},
        )
        self.assertEqual(resumed_status.status_code, 200, resumed_status.text)
        self.assertGreater(
            resumed_status.json()["data"]["expires_at"],
            original_expires_at,
        )
        self.assertFalse(resumed_status.json()["data"]["timer_frozen"])


if __name__ == "__main__":
    unittest.main()
