"""Web console routes for browser-based student and proctor operations."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter(tags=["web"])


def _repo_root() -> Path:
    if getattr(sys, "frozen", False):
        bundled_root = getattr(sys, "_MEIPASS", None)
        if bundled_root:
            return Path(str(bundled_root))
    return Path(__file__).resolve().parents[2]


def _web_index_path() -> Path:
    return _repo_root() / "phase1_server" / "web" / "index.html"


def _web_asset_path(asset_path: str) -> Path:
    root = (_repo_root() / "phase1_server" / "web").resolve()
    candidate = (root / asset_path).resolve()
    if root != candidate and root not in candidate.parents:
        raise HTTPException(status_code=404, detail="Asset not found")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return candidate


@router.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/web")


@router.get("/web", include_in_schema=False)
@router.get("/web/", include_in_schema=False)
def serve_web_console() -> FileResponse:
    index_path = _web_index_path()
    if not index_path.exists():
        raise HTTPException(status_code=503, detail="Web console asset is missing")
    return FileResponse(index_path)


@router.get("/web/{asset_path:path}", include_in_schema=False)
def serve_web_asset(asset_path: str) -> FileResponse:
    return FileResponse(_web_asset_path(asset_path))
