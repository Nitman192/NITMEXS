import os
import tempfile
import unittest
from pathlib import Path

from phase1_server.logging_config import configure_logging
from phase1_server.settings import AppSettings, load_settings

try:
    from fastapi.testclient import TestClient
    from phase1_server.app import create_app

    FASTAPI_AVAILABLE = True
except Exception:
    TestClient = None
    create_app = None
    FASTAPI_AVAILABLE = False


class DeploymentHardeningTests(unittest.TestCase):
    def test_config_loading_from_yaml_and_env(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as fh:
            fh.write(
                "\n".join(
                    [
                        "host: 0.0.0.0",
                        "port: 9001",
                        "db_path: ./tmp/test.db",
                        "log_level: DEBUG",
                        "version: 2.0.0",
                    ]
                )
            )
            config_path = fh.name

        try:
            os.environ["NITMEXS_PORT"] = "9100"
            settings = load_settings(config_path)
        finally:
            os.environ.pop("NITMEXS_PORT", None)
            Path(config_path).unlink(missing_ok=True)

        self.assertEqual(settings.host, "0.0.0.0")
        self.assertEqual(settings.port, 9100)
        self.assertEqual(settings.db_path, "./tmp/test.db")
        self.assertEqual(settings.log_level, "DEBUG")
        self.assertEqual(settings.version, "2.0.0")

    def test_logging_initialization_creates_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            app_log = str(Path(tmp_dir) / "app.log")
            audit_log = str(Path(tmp_dir) / "audit.log")
            settings = AppSettings(
                app_log_path=app_log,
                audit_log_path=audit_log,
                log_level="INFO",
            )
            configure_logging(settings)

            self.assertTrue(Path(app_log).exists())
            self.assertTrue(Path(audit_log).exists())

    @unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI test client unavailable")
    def test_version_endpoint(self):
        settings = AppSettings(version="9.9.9")
        app = create_app(settings=settings)
        with TestClient(app) as client:
            response = client.get("/system/version")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["version"], "9.9.9")


if __name__ == "__main__":
    unittest.main()
