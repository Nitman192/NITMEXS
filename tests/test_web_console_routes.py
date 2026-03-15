import tempfile
import unittest
from pathlib import Path

try:
    from fastapi.testclient import TestClient
    from phase1_server.app import create_app

    FASTAPI_AVAILABLE = True
except Exception:
    TestClient = None
    create_app = None
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
class WebConsoleRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "web_routes.db")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_root_redirects_to_web(self):
        app = create_app(db_path=self.db_path)
        with TestClient(app) as client:
            response = client.get("/", follow_redirects=False)

        self.assertIn(response.status_code, (302, 307))
        self.assertEqual(response.headers.get("location"), "/web")

    def test_web_console_assets_are_served(self):
        app = create_app(db_path=self.db_path)
        with TestClient(app) as client:
            index_response = client.get("/web")
            index_js_response = client.get("/web/index.js")
            theme_toggle_response = client.get("/web/theme_toggle.js")
            theme_response = client.get("/web/theme.css")
            student_response = client.get("/web/student.html")
            student_js_response = client.get("/web/student.js")
            admin_response = client.get("/web/admin.html")
            admin_js_response = client.get("/web/admin.js")
            demo_question_csv_response = client.get("/web/demo_question_bank.csv")
            demo_exam_pack_csv_response = client.get("/web/demo_exam_package.csv")
            demo_student_csv_response = client.get("/web/demo_student_ids.csv")

        self.assertEqual(index_response.status_code, 200)
        self.assertIn("text/html", index_response.headers.get("content-type", ""))
        self.assertIn("Web Control Gateway", index_response.text)
        self.assertIn("NITMEXS EXAM SYSTEM", index_response.text)
        self.assertIn("Student Login", index_response.text)
        self.assertIn("Admin Login", index_response.text)
        self.assertIn("Login As Cadet", index_response.text)
        self.assertIn("Login As Exam Controller", index_response.text)
        self.assertIn("student-login-password", index_response.text)

        self.assertEqual(index_js_response.status_code, 200)
        self.assertIn("javascript", index_js_response.headers.get("content-type", ""))
        self.assertIn("version-badge", index_js_response.text)
        self.assertIn("access-profile-label", index_js_response.text)
        self.assertIn("loadPortalContext", index_js_response.text)

        self.assertEqual(theme_toggle_response.status_code, 200)
        self.assertIn("javascript", theme_toggle_response.headers.get("content-type", ""))
        self.assertIn("nitmexs_theme_mode", theme_toggle_response.text)

        self.assertEqual(theme_response.status_code, 200)
        self.assertIn("text/css", theme_response.headers.get("content-type", ""))
        self.assertIn("--bg", theme_response.text)

        self.assertEqual(student_response.status_code, 200)
        self.assertIn("NITMEXS EXAM MODE", student_response.text)
        self.assertIn("Cadet Examination Console", student_response.text)
        self.assertIn("Question Viewer", student_response.text)
        self.assertIn("Submit Exam", student_response.text)
        self.assertIn("High Contrast", student_response.text)
        self.assertIn("Pre-Exam Lobby", student_response.text)
        self.assertIn("Exam Submission", student_response.text)
        self.assertIn("Jump to First Unanswered", student_response.text)
        self.assertIn("Shortcuts", student_response.text)
        self.assertIn("Reference Exam", student_response.text)
        self.assertIn("Device Diagnostics", student_response.text)
        self.assertIn("Exam Support Panel", student_response.text)
        self.assertIn("Diagram Canvas", student_response.text)
        self.assertIn("Input Tools", student_response.text)
        self.assertIn("Live Status Tracker", student_response.text)
        self.assertNotIn("Post-Exam Analysis", student_response.text)
        self.assertNotIn("Analyze Exam", student_response.text)
        self.assertNotIn("Practice Simulation", student_response.text)
        self.assertNotIn("Topic strength map", student_response.text)

        self.assertEqual(student_js_response.status_code, 200)
        self.assertIn("startAttempt", student_js_response.text)
        self.assertIn("renderAnswer", student_js_response.text)
        self.assertIn("buildKeyboard", student_js_response.text)
        self.assertIn("jumpFirstUnanswered", student_js_response.text)
        self.assertIn("pollBroadcasts", student_js_response.text)
        self.assertIn("bindCanvas", student_js_response.text)
        self.assertIn("bindSecurity", student_js_response.text)
        self.assertIn("bindShortcuts", student_js_response.text)
        self.assertIn("loadRulesPreview", student_js_response.text)
        self.assertIn("broadcastModal", student_js_response.text)
        self.assertIn("setStage(", student_js_response.text)
        self.assertIn("finalize(", student_js_response.text)
        self.assertIn("/student/attempts/", student_js_response.text)
        self.assertNotIn("renderAiAnalysis", student_js_response.text)
        self.assertNotIn("runPracticeSimulation", student_js_response.text)
        self.assertNotIn("playQuestionAudio", student_js_response.text)

        self.assertEqual(admin_response.status_code, 200)
        self.assertIn("NITMEXS Exam Controller Console", admin_response.text)
        self.assertIn("Exam Scope", admin_response.text)
        self.assertIn("Question Authoring", admin_response.text)
        self.assertIn("Cadet Registry", admin_response.text)
        self.assertIn("Custom Exam Rules", admin_response.text)
        self.assertIn("Admin Accounts", admin_response.text)
        self.assertIn("FIB Review Queue", admin_response.text)
        self.assertIn("Subjective Review Queue", admin_response.text)
        self.assertIn("Emergency STOP", admin_response.text)
        self.assertIn("Force Submit Attempt", admin_response.text)
        self.assertIn("Force Submit Expired", admin_response.text)
        self.assertIn("Send Broadcast", admin_response.text)
        self.assertIn("Resume Paused Attempts", admin_response.text)
        self.assertIn("Delete Selected Exam", admin_response.text)
        self.assertIn("System Security", admin_response.text)
        self.assertIn("Results and Reports", admin_response.text)
        self.assertIn("analytics-shell", admin_response.text)
        self.assertNotIn("Publish and Safety Studio", admin_response.text)
        self.assertNotIn("AI Draft + Human Review Lane", admin_response.text)

        self.assertEqual(admin_js_response.status_code, 200)
        self.assertIn("createExam", admin_js_response.text)
        self.assertIn("createQuestion", admin_js_response.text)
        self.assertIn("/admin/students/import-csv", admin_js_response.text)
        self.assertIn("loadFibReview", admin_js_response.text)
        self.assertIn("loadSubjectiveReview", admin_js_response.text)
        self.assertIn("attachQuestionToExam", admin_js_response.text)
        self.assertIn("forceSubmitAttempt", admin_js_response.text)
        self.assertIn("forceSubmitExpired", admin_js_response.text)
        self.assertIn("publishExam", admin_js_response.text)
        self.assertIn("closeExam", admin_js_response.text)
        self.assertIn("sendBroadcast", admin_js_response.text)
        self.assertIn("deleteExam", admin_js_response.text)
        self.assertIn("loadMetrics", admin_js_response.text)
        self.assertIn("renderAnalyticsDashboard", admin_js_response.text)
        self.assertIn("score-distribution", admin_js_response.text)
        self.assertIn("topic-heatmap", admin_js_response.text)
        self.assertIn("saveCustomRules", admin_js_response.text)
        self.assertIn("createAdminAccount", admin_js_response.text)
        self.assertNotIn("generateAiDraft", admin_js_response.text)

        self.assertEqual(demo_question_csv_response.status_code, 200)
        self.assertTrue(
            any(
                token in demo_question_csv_response.headers.get("content-type", "")
                for token in ("text/csv", "application/vnd.ms-excel")
            )
        )
        self.assertIn("question_type", demo_question_csv_response.text)

        self.assertEqual(demo_exam_pack_csv_response.status_code, 200)
        self.assertTrue(
            any(
                token in demo_exam_pack_csv_response.headers.get("content-type", "")
                for token in ("text/csv", "application/vnd.ms-excel")
            )
        )
        self.assertIn("exam_name", demo_exam_pack_csv_response.text)
        self.assertIn("question_type", demo_exam_pack_csv_response.text)

        self.assertEqual(demo_student_csv_response.status_code, 200)
        self.assertTrue(
            any(
                token in demo_student_csv_response.headers.get("content-type", "")
                for token in ("text/csv", "application/vnd.ms-excel")
            )
        )
        self.assertIn("student_id", demo_student_csv_response.text)
        self.assertIn("password", demo_student_csv_response.text)


if __name__ == "__main__":
    unittest.main()
