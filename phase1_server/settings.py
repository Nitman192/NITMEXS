"""Application configuration loading for deployment hardening."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppSettings:
    host: str = "127.0.0.1"
    port: int = 8000
    db_path: str = "./data/exam_server.db"
    log_level: str = "INFO"
    app_log_path: str = "./logs/app.log"
    audit_log_path: str = "./logs/audit.log"
    version: str = "1.0.0"
    ai_provider: str = "auto"
    ai_model: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    openai_model: str = ""
    gemini_model: str = ""


def _coerce_value(value: str) -> Any:
    text = value.strip()
    if text.isdigit():
        return int(text)
    return text.strip('"').strip("'")


def _parse_simple_yaml(path: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    content = Path(path).read_text(encoding="utf-8")
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = _coerce_value(value)
    return data


def load_settings(config_path: str | None = None) -> AppSettings:
    values: dict[str, Any] = {}
    resolved_path = config_path or os.getenv("NITMEXS_CONFIG")
    if resolved_path and Path(resolved_path).exists():
        values.update(_parse_simple_yaml(resolved_path))

    env_map = {
        "host": os.getenv("NITMEXS_HOST"),
        "port": os.getenv("NITMEXS_PORT"),
        "db_path": os.getenv("NITMEXS_DB_PATH"),
        "log_level": os.getenv("NITMEXS_LOG_LEVEL"),
        "app_log_path": os.getenv("NITMEXS_APP_LOG_PATH"),
        "audit_log_path": os.getenv("NITMEXS_AUDIT_LOG_PATH"),
        "version": os.getenv("NITMEXS_VERSION"),
        "ai_provider": os.getenv("NITMEXS_AI_PROVIDER"),
        "ai_model": os.getenv("NITMEXS_AI_MODEL"),
        "openai_api_key": os.getenv("NITMEXS_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"),
        "gemini_api_key": os.getenv("NITMEXS_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY"),
        "openai_model": os.getenv("NITMEXS_OPENAI_MODEL"),
        "gemini_model": os.getenv("NITMEXS_GEMINI_MODEL"),
    }
    for key, value in env_map.items():
        if value is not None:
            values[key] = _coerce_value(value)

    return AppSettings(
        host=str(values.get("host", AppSettings.host)),
        port=int(values.get("port", AppSettings.port)),
        db_path=str(values.get("db_path", AppSettings.db_path)),
        log_level=str(values.get("log_level", AppSettings.log_level)).upper(),
        app_log_path=str(values.get("app_log_path", AppSettings.app_log_path)),
        audit_log_path=str(values.get("audit_log_path", AppSettings.audit_log_path)),
        version=str(values.get("version", AppSettings.version)),
        ai_provider=str(values.get("ai_provider", AppSettings.ai_provider)).strip() or AppSettings.ai_provider,
        ai_model=str(values.get("ai_model", AppSettings.ai_model)).strip(),
        openai_api_key=str(values.get("openai_api_key", AppSettings.openai_api_key)).strip(),
        gemini_api_key=str(values.get("gemini_api_key", AppSettings.gemini_api_key)).strip(),
        openai_model=str(values.get("openai_model", AppSettings.openai_model)).strip(),
        gemini_model=str(values.get("gemini_model", AppSettings.gemini_model)).strip(),
    )


def apply_runtime_environment(settings: AppSettings) -> None:
    runtime_values = {
        "NITMEXS_AI_PROVIDER": settings.ai_provider,
        "NITMEXS_AI_MODEL": settings.ai_model,
        "NITMEXS_OPENAI_API_KEY": settings.openai_api_key,
        "NITMEXS_GEMINI_API_KEY": settings.gemini_api_key,
        "NITMEXS_OPENAI_MODEL": settings.openai_model,
        "NITMEXS_GEMINI_MODEL": settings.gemini_model,
    }
    for key, value in runtime_values.items():
        if value:
            os.environ[key] = str(value)
