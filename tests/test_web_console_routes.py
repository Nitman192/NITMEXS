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
            js_response = client.get("/web/app.js")

        self.assertEqual(index_response.status_code, 200)
        self.assertIn("text/html", index_response.headers.get("content-type", ""))
        self.assertIn("NITMEXS Web Console", index_response.text)

        self.assertEqual(js_response.status_code, 200)
        self.assertIn("javascript", js_response.headers.get("content-type", ""))
        self.assertIn("loadVersion", js_response.text)


if __name__ == "__main__":
    unittest.main()
