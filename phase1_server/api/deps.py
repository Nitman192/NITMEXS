"""API dependencies."""

from __future__ import annotations

from fastapi import Header, HTTPException


def admin_only(x_admin: str | None = Header(default=None)) -> None:
    if x_admin != "true":
        raise HTTPException(status_code=403, detail="Admin access required")


def student_identity(
    x_student_id: str | None = Header(default=None),
    x_admin: str | None = Header(default=None),
) -> str:
    if x_admin == "true":
        raise HTTPException(status_code=403, detail="Student access required")
    if not x_student_id:
        raise HTTPException(status_code=401, detail="Missing student identity")
    return x_student_id
