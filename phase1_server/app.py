"""FastAPI application entrypoint for LAN examination server."""

from __future__ import annotations

import logging
import logging as pylogging
import time

from fastapi import FastAPI, Request

from phase1_server.api.admin_routes import router as admin_router
from phase1_server.api.student_routes import router as student_router
from phase1_server.api.system_routes import router as system_router
from phase1_server.db import Database, SQLiteConfig
from phase1_server.logging_config import configure_logging
from phase1_server.schema_version import EXPECTED_SCHEMA_VERSION
from phase1_server.services.metrics_service import MetricsService
from phase1_server.settings import AppSettings, load_settings
from phase1_server.uow import UnitOfWork


def create_app(
    db_path: str | None = None,
    settings: AppSettings | None = None,
) -> FastAPI:
    active_settings = settings or load_settings()
    if db_path is not None:
        active_settings = AppSettings(
            host=active_settings.host,
            port=active_settings.port,
            db_path=db_path,
            log_level=active_settings.log_level,
            app_log_path=active_settings.app_log_path,
            audit_log_path=active_settings.audit_log_path,
            version=active_settings.version,
        )

    configure_logging(active_settings)
    logger = logging.getLogger("phase1_server")

    app = FastAPI(title="NITMEXS LAN Server")
    db = Database(SQLiteConfig(db_path=active_settings.db_path))
    db.initialize()
    db.ensure_expected_schema_version(EXPECTED_SCHEMA_VERSION)

    app.state.db = db
    app.state.settings = active_settings
    app.state.logger = logger

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0

        try:
            with UnitOfWork(db) as uow:
                MetricsService(uow.metrics).record_request_duration(
                    endpoint=f"{request.method} {request.url.path}",
                    duration_ms=duration_ms,
                )
        except Exception:
            logger.exception("metrics_recording_failed")

        return response

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        try:
            db.close()
        finally:
            pylogging.shutdown()

    app.include_router(admin_router)
    app.include_router(student_router)
    app.include_router(system_router)
    return app


app = create_app()
