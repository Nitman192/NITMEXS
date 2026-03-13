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
        self.assertIn("High Contrast", student_response.text)
        self.assertIn("Pre-Exam Lobby", student_response.text)
        self.assertIn("Post-Exam Analysis", student_response.text)
        self.assertIn("Analyze Exam", student_response.text)
        self.assertIn("Jump to First Unanswered", student_response.text)
        self.assertIn("Mini Progress", student_response.text)
        self.assertIn("Answer Timeline", student_response.text)
        self.assertIn("Shortcuts", student_response.text)
        self.assertIn("Pre-download Questions", student_response.text)
        self.assertIn("Rough Pad", student_response.text)
        self.assertIn("Instant Support", student_response.text)
        self.assertIn("Diagram Canvas", student_response.text)
        self.assertIn("Practice Simulation", student_response.text)
        self.assertIn("Topic strength map", student_response.text)
        self.assertNotIn("Student Cockpit", student_response.text)
        self.assertNotIn("Question Deck", student_response.text)

        self.assertEqual(student_js_response.status_code, 200)
        self.assertIn("startAttempt", student_js_response.text)
        self.assertIn("createTimerState", student_js_response.text)
        self.assertIn("createAnswerState", student_js_response.text)
        self.assertIn("STUDENT_ONBOARDING_KEY", student_js_response.text)
        self.assertIn("jumpToFirstUnanswered", student_js_response.text)
        self.assertIn("acknowledgeBroadcastReceipts", student_js_response.text)
        self.assertIn("setPausedState", student_js_response.text)
        self.assertIn("predownloadOfflinePacket", student_js_response.text)
        self.assertIn("toggleHardBucket", student_js_response.text)
        self.assertIn("openResumeWizard", student_js_response.text)
        self.assertIn("runPracticeSimulation", student_js_response.text)
        self.assertIn("initializeDiagramCanvas", student_js_response.text)
        self.assertIn("renderTopicStrengthAndWeakPlan", student_js_response.text)
        self.assertIn("playQuestionAudio", student_js_response.text)
        self.assertIn("setStage(", student_js_response.text)
        self.assertIn("renderAiAnalysis", student_js_response.text)
        self.assertIn("loadPostExamInsights", student_js_response.text)
        self.assertIn("/analysis/explain", student_js_response.text)

        self.assertEqual(admin_response.status_code, 200)
        self.assertIn("Admin Command Center", admin_response.text)
        self.assertIn("Idle lock timeout", admin_response.text)
        self.assertIn("Import Student CSV", admin_response.text)
        self.assertIn("Read Receipts", admin_response.text)
        self.assertIn("Run Preflight Report", admin_response.text)
        self.assertIn("Compute Risk Model", admin_response.text)
        self.assertIn("Export SIEM JSON", admin_response.text)
        self.assertIn("Hash Audit Chain", admin_response.text)
        self.assertIn("Emergency STOP", admin_response.text)
        self.assertIn("Force Submit Attempt", admin_response.text)
        self.assertIn("Force Submit Expired", admin_response.text)
        self.assertIn("Send Broadcast", admin_response.text)
        self.assertIn("Resume Paused Attempts", admin_response.text)
        self.assertIn("Delete Selected Exam", admin_response.text)
        self.assertIn("Publish and Safety Studio", admin_response.text)
        self.assertIn("AI Draft + Human Review Lane", admin_response.text)
        self.assertIn("Advanced Analytics Studio", admin_response.text)
        self.assertIn("Backup and Access Security", admin_response.text)

        self.assertEqual(admin_js_response.status_code, 200)
        self.assertIn("toggleAutoPolling", admin_js_response.text)
        self.assertIn("IDLE_TIMEOUT_POLICY_KEY", admin_js_response.text)
        self.assertIn("/admin/students/import-csv", admin_js_response.text)
        self.assertIn("refreshBroadcastReceipts", admin_js_response.text)
        self.assertIn("toggleAutoForceExpiredPolicy", admin_js_response.text)
        self.assertIn("computeRiskModel", admin_js_response.text)
        self.assertIn("exportSiemJson", admin_js_response.text)
        self.assertIn("applyComplianceProfile", admin_js_response.text)
        self.assertIn("saveWidgetLayout", admin_js_response.text)
        self.assertIn("forceSubmitAttempt", admin_js_response.text)
        self.assertIn("forceSubmitExpired", admin_js_response.text)
        self.assertIn("pauseExam", admin_js_response.text)
        self.assertIn("resumeExam", admin_js_response.text)
        self.assertIn("sendBroadcast", admin_js_response.text)
        self.assertIn("deleteSelectedExam", admin_js_response.text)
        self.assertIn("runCanaryPublish", admin_js_response.text)
        self.assertIn("applyCircuitBreakerRule", admin_js_response.text)
        self.assertIn("runRestoreDrySandbox", admin_js_response.text)
        self.assertIn("runDbProfiler", admin_js_response.text)
        self.assertIn("generateAiDraft", admin_js_response.text)

        self.assertEqual(demo_question_csv_response.status_code, 200)
        self.assertTrue(
            any(
                token in demo_question_csv_response.headers.get("content-type", "")
                for token in ("text/csv", "application/vnd.ms-excel")
            )
        )
        self.assertIn("correct_option", demo_question_csv_response.text)

        self.assertEqual(demo_exam_pack_csv_response.status_code, 200)
        self.assertTrue(
            any(
                token in demo_exam_pack_csv_response.headers.get("content-type", "")
                for token in ("text/csv", "application/vnd.ms-excel")
            )
        )
        self.assertIn("exam_name", demo_exam_pack_csv_response.text)

        self.assertEqual(demo_student_csv_response.status_code, 200)
        self.assertTrue(
            any(
                token in demo_student_csv_response.headers.get("content-type", "")
                for token in ("text/csv", "application/vnd.ms-excel")
            )
        )
        self.assertIn("student_id", demo_student_csv_response.text)


if __name__ == "__main__":
    unittest.main()
