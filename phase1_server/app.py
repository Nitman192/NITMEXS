"""FastAPI application entrypoint for LAN examination server."""

from __future__ import annotations

import time

from fastapi import FastAPI, Request

from phase1_server.api.admin_routes import router as admin_router
from phase1_server.api.student_routes import router as student_router
from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.metrics_service import MetricsService
from phase1_server.uow import UnitOfWork


def create_app(db_path: str = "./data/exam_server.db") -> FastAPI:
    app = FastAPI(title="NITMEXS LAN Server")
    db = Database(SQLiteConfig(db_path=db_path))
    db.initialize()
    app.state.db = db

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
            pass

        return response
    app.include_router(admin_router)
    app.include_router(student_router)
    return app


app = create_app()
