"""System-level routes for deployment diagnostics."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/version")
def get_version(request: Request):
    return {
        "status": "success",
        "data": {"version": request.app.state.settings.version},
    }
