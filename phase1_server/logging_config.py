"""Structured logging initialization for the backend."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from phase1_server.settings import AppSettings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def _create_handler(path: str, level: str) -> RotatingFileHandler:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(path, maxBytes=1_048_576, backupCount=3)
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    return handler


def _reset_logger_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.flush()
            handler.close()
        except Exception:
            continue


def configure_logging(settings: AppSettings) -> None:
    app_logger = logging.getLogger("phase1_server")
    audit_logger = logging.getLogger("phase1_server.audit")

    _reset_logger_handlers(app_logger)
    _reset_logger_handlers(audit_logger)

    app_logger.setLevel(settings.log_level)
    audit_logger.setLevel(settings.log_level)

    app_handler = _create_handler(settings.app_log_path, settings.log_level)
    audit_handler = _create_handler(settings.audit_log_path, settings.log_level)

    app_logger.addHandler(app_handler)
    audit_logger.addHandler(audit_handler)

    app_logger.propagate = False
    audit_logger.propagate = False

    app_logger.info("logging_initialized")
