"""API dependencies."""

from __future__ import annotations

from fastapi import Header, HTTPException, Request

from phase1_server.services.audit_service import AuditService
from phase1_server.services.admin_account_service import AdminAccountService
from phase1_server.services.deployment_service import DeploymentProfileService
from phase1_server.uow import UnitOfWork


def admin_only(
    request: Request,
    x_admin: str | None = Header(default=None),
    x_admin_id: str | None = Header(default=None),
) -> None:
    if x_admin != "true":
        raise HTTPException(status_code=403, detail="Admin access required")
    with UnitOfWork(request.app.state.db) as uow:
        service = DeploymentProfileService(
            uow.deployment_settings,
            audit_service=AuditService(uow.audit_events),
        )
        request_host = (request.client.host if request.client else "") or ""
        if not service.is_host_request(request_host):
            try:
                AuditService(uow.audit_events).log_event(
                    entity_type="deployment",
                    entity_id="deployment_settings",
                    actor_type="remote_client",
                    actor_id=request_host or "unknown",
                    event_type="ADMIN_ACCESS_BLOCKED",
                    payload={"path": request.url.path, "request_host": request_host},
                )
            except Exception:
                pass
            raise HTTPException(status_code=403, detail="Admin access is allowed only from the trusted host machine")
        request.state.admin_identity = AdminAccountService(uow.admin_accounts).resolve_identity(
            x_admin_id
        )


def student_identity(
    request: Request,
    x_student_id: str | None = Header(default=None),
    x_admin: str | None = Header(default=None),
) -> str:
    if x_admin == "true":
        raise HTTPException(status_code=403, detail="Student access required")
    if not x_student_id:
        raise HTTPException(status_code=401, detail="Missing student identity")
    return x_student_id
