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

        self.assertEqual(index_response.status_code, 200)
        self.assertIn("text/html", index_response.headers.get("content-type", ""))
        self.assertIn("Web Control Gateway", index_response.text)
        self.assertIn("Login As Student", index_response.text)
        self.assertIn("Login As Admin", index_response.text)

        self.assertEqual(index_js_response.status_code, 200)
        self.assertIn("javascript", index_js_response.headers.get("content-type", ""))
        self.assertIn("version-badge", index_js_response.text)

        self.assertEqual(theme_toggle_response.status_code, 200)
        self.assertIn("javascript", theme_toggle_response.headers.get("content-type", ""))
        self.assertIn("nitmexs_theme_mode", theme_toggle_response.text)

        self.assertEqual(theme_response.status_code, 200)
        self.assertIn("text/css", theme_response.headers.get("content-type", ""))
        self.assertIn("--bg", theme_response.text)

        self.assertEqual(student_response.status_code, 200)
        self.assertIn("Student Dashboard", student_response.text)
        self.assertIn("Question Viewer", student_response.text)
        self.assertIn("Submit Exam", student_response.text)
        self.assertNotIn("Student Cockpit", student_response.text)
        self.assertNotIn("Question Deck", student_response.text)

        self.assertEqual(student_js_response.status_code, 200)
        self.assertIn("startAttempt", student_js_response.text)
        self.assertIn("createTimerState", student_js_response.text)
        self.assertIn("createAnswerState", student_js_response.text)

        self.assertEqual(admin_response.status_code, 200)
        self.assertIn("Admin Command Center", admin_response.text)

        self.assertEqual(admin_js_response.status_code, 200)
        self.assertIn("toggleAutoPolling", admin_js_response.text)

        self.assertEqual(demo_question_csv_response.status_code, 200)
        self.assertTrue(
            any(
                token in demo_question_csv_response.headers.get("content-type", "")
                for token in ("text/csv", "application/vnd.ms-excel")
            )
        )
        self.assertIn("option1_is_correct", demo_question_csv_response.text)

        self.assertEqual(demo_exam_pack_csv_response.status_code, 200)
        self.assertTrue(
            any(
                token in demo_exam_pack_csv_response.headers.get("content-type", "")
                for token in ("text/csv", "application/vnd.ms-excel")
            )
        )
        self.assertIn("exam_name", demo_exam_pack_csv_response.text)


if __name__ == "__main__":
    unittest.main()
