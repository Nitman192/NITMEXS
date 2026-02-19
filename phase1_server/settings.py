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
    )
