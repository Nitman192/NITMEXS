"""System-level routes for deployment diagnostics."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from phase1_server.schemas import AdminLoginSchema
from phase1_server.services.admin_account_service import (
    AdminAccountService,
    AdminAuthenticationError,
)
from phase1_server.services.audit_service import AuditService
from phase1_server.services.deployment_service import DeploymentProfileService
from phase1_server.uow import UnitOfWork

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/version")
def get_version(request: Request):
    return {
        "status": "success",
        "data": {"version": request.app.state.settings.version},
    }


@router.get("/access-profile")
def get_access_profile(request: Request):
    with UnitOfWork(request.app.state.db) as uow:
        service = DeploymentProfileService(
            uow.deployment_settings,
            audit_service=AuditService(uow.audit_events),
        )
        access_profile = service.resolve_access_profile(
            (request.client.host if request.client else "") or ""
        )
    return {
        "status": "success",
        "data": {
            "request_machine_type": access_profile.request_machine_type,
            "admin_visible": access_profile.admin_visible,
            "student_visible": access_profile.student_visible,
            "deployment_profile": access_profile.deployment_profile,
            "branding_profile": access_profile.branding_profile,
        },
    }


@router.post("/admin-login")
def admin_login(payload: AdminLoginSchema, request: Request):
    with UnitOfWork(request.app.state.db) as uow:
        deployment_service = DeploymentProfileService(
            uow.deployment_settings,
            audit_service=AuditService(uow.audit_events),
        )
        request_host = (request.client.host if request.client else "") or ""
        if not deployment_service.is_host_request(request_host):
            raise HTTPException(
                status_code=403,
                detail="Admin login is allowed only from the trusted host machine",
            )
        service = AdminAccountService(uow.admin_accounts)
        try:
            identity = service.authenticate(payload.admin_id, payload.access_key)
        except AdminAuthenticationError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {
        "status": "success",
        "data": {
            "admin_id": identity.admin_id,
            "role": identity.role.value,
            "display_name": identity.display_name,
        },
    }
