"""FastAPI application entrypoint for LAN examination server."""

from __future__ import annotations

from fastapi import FastAPI

from phase1_server.api.admin_routes import router as admin_router
from phase1_server.api.student_routes import router as student_router
from phase1_server.db import Database, SQLiteConfig


def create_app(db_path: str = "./data/exam_server.db") -> FastAPI:
    app = FastAPI(title="NITMEXS LAN Server")
    db = Database(SQLiteConfig(db_path=db_path))
    db.initialize()
    app.state.db = db
    app.include_router(admin_router)
    app.include_router(student_router)
    return app


app = create_app()
