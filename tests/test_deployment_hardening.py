import logging
import os
import tempfile
import unittest
from pathlib import Path

from phase1_server.logging_config import configure_logging
from phase1_server.settings import AppSettings, apply_runtime_environment, load_settings

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
                        "ai_provider: gemini",
                        "gemini_api_key: test-gemini-key",
                        "gemini_model: gemini-2.5-flash",
                    ]
                )
            )
            config_path = fh.name

        try:
            original_ai_env = {
                "NITMEXS_AI_PROVIDER": os.environ.get("NITMEXS_AI_PROVIDER"),
                "NITMEXS_GEMINI_API_KEY": os.environ.get("NITMEXS_GEMINI_API_KEY"),
                "NITMEXS_GEMINI_MODEL": os.environ.get("NITMEXS_GEMINI_MODEL"),
                "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
            }
            for key in original_ai_env:
                os.environ.pop(key, None)
            os.environ["NITMEXS_PORT"] = "9100"
            settings = load_settings(config_path)
        finally:
            os.environ.pop("NITMEXS_PORT", None)
            for key, value in original_ai_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            Path(config_path).unlink(missing_ok=True)

        self.assertEqual(settings.host, "0.0.0.0")
        self.assertEqual(settings.port, 9100)
        self.assertEqual(settings.db_path, "./tmp/test.db")
        self.assertEqual(settings.log_level, "DEBUG")
        self.assertEqual(settings.version, "2.0.0")
        self.assertEqual(settings.ai_provider, "gemini")
        self.assertEqual(settings.gemini_api_key, "test-gemini-key")
        self.assertEqual(settings.gemini_model, "gemini-2.5-flash")

    def test_apply_runtime_environment_sets_ai_variables(self):
        tracked_keys = [
            "NITMEXS_AI_PROVIDER",
            "NITMEXS_AI_MODEL",
            "NITMEXS_OPENAI_API_KEY",
            "NITMEXS_GEMINI_API_KEY",
            "NITMEXS_OPENAI_MODEL",
            "NITMEXS_GEMINI_MODEL",
        ]
        original = {key: os.environ.get(key) for key in tracked_keys}
        try:
            for key in tracked_keys:
                os.environ.pop(key, None)
            settings = AppSettings(
                ai_provider="openai",
                ai_model="gpt-4.1-mini",
                openai_api_key="test-openai-key",
                gemini_api_key="test-gemini-key",
                openai_model="gpt-4.1-mini",
                gemini_model="gemini-2.5-flash",
            )
            apply_runtime_environment(settings)
            self.assertEqual(os.environ.get("NITMEXS_AI_PROVIDER"), "openai")
            self.assertEqual(os.environ.get("NITMEXS_AI_MODEL"), "gpt-4.1-mini")
            self.assertEqual(os.environ.get("NITMEXS_OPENAI_API_KEY"), "test-openai-key")
            self.assertEqual(os.environ.get("NITMEXS_GEMINI_API_KEY"), "test-gemini-key")
            self.assertEqual(os.environ.get("NITMEXS_OPENAI_MODEL"), "gpt-4.1-mini")
            self.assertEqual(os.environ.get("NITMEXS_GEMINI_MODEL"), "gemini-2.5-flash")
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

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
            logging.shutdown()
            logging.getLogger("phase1_server").handlers.clear()
            logging.getLogger("phase1_server.audit").handlers.clear()

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
