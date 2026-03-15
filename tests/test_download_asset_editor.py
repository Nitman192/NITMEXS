import os
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
class DownloadAssetEditorTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "download_assets.db")
        self.web_root = Path(self.tmp_dir.name) / "web_assets"
        self.web_root.mkdir(parents=True, exist_ok=True)
        (self.web_root / "custom_downloads").mkdir(parents=True, exist_ok=True)
        (self.web_root / "manual_admin.html").write_text("<h1>Admin Manual</h1>", encoding="utf-8")
        (self.web_root / "demo_question_bank.csv").write_text("question_type,text\nmcq_single,Sample\n", encoding="utf-8")
        (self.web_root / "nitmexs_config_sample.yaml").write_text("ai_mode: local_sidecar\n", encoding="utf-8")
        self.previous_asset_root = os.environ.get("NITMEXS_WEB_ASSET_ROOT")
        os.environ["NITMEXS_WEB_ASSET_ROOT"] = str(self.web_root)

    def tearDown(self):
        if self.previous_asset_root is None:
            os.environ.pop("NITMEXS_WEB_ASSET_ROOT", None)
        else:
            os.environ["NITMEXS_WEB_ASSET_ROOT"] = self.previous_asset_root
        self.tmp_dir.cleanup()

    def test_download_assets_can_be_listed_read_updated_and_created(self):
        app = create_app(db_path=self.db_path)
        headers = {"x-admin": "true", "x-admin-id": "superadmin"}
        with TestClient(app) as client:
            listing = client.get("/admin/download-assets", headers=headers)
            self.assertEqual(listing.status_code, 200)
            names = [item["file_name"] for item in listing.json()["data"]]
            self.assertIn("manual_admin.html", names)
            self.assertIn("demo_question_bank.csv", names)

            loaded = client.get("/admin/download-assets/manual_admin.html", headers=headers)
            self.assertEqual(loaded.status_code, 200)
            self.assertIn("Admin Manual", loaded.json()["data"]["content"])

            updated = client.put(
                "/admin/download-assets/manual_admin.html",
                headers=headers,
                json={"content": "<h1>Updated Manual</h1>"},
            )
            self.assertEqual(updated.status_code, 200)
            self.assertIn("Updated Manual", (self.web_root / "manual_admin.html").read_text(encoding="utf-8"))

            created = client.post(
                "/admin/download-assets",
                headers=headers,
                json={"file_name": "notice_board.html", "content": "<p>New notice</p>"},
            )
            self.assertEqual(created.status_code, 201)
            self.assertTrue((self.web_root / "custom_downloads" / "notice_board.html").exists())

            custom_loaded = client.get(
                "/admin/download-assets/custom_downloads/notice_board.html",
                headers=headers,
            )
            self.assertEqual(custom_loaded.status_code, 200)
            self.assertIn("New notice", custom_loaded.json()["data"]["content"])


if __name__ == "__main__":
    unittest.main()
