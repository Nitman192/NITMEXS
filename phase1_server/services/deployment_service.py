"""Deployment profile and trusted-host access control helpers."""

from __future__ import annotations

import hashlib
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from phase1_server.models import DeploymentSettings
from phase1_server.repositories.deployment_repository import DeploymentSettingsRepository
from phase1_server.services.audit_service import AuditService

try:
    import winreg  # type: ignore
except ImportError:  # pragma: no cover
    winreg = None


class DeploymentSettingsError(ValueError):
    pass


@dataclass(frozen=True)
class AccessProfile:
    request_machine_type: str
    admin_visible: bool
    student_visible: bool
    deployment_profile: str
    branding_profile: str


class DeploymentProfileService:
    def __init__(
        self,
        repo: DeploymentSettingsRepository,
        audit_service: AuditService | None = None,
    ):
        self._repo = repo
        self._audit_service = audit_service

    def ensure_initialized(self) -> DeploymentSettings:
        settings = self._repo.get()
        if settings is None:
            raise DeploymentSettingsError("Deployment settings are not initialized")

        current_fingerprint = self.current_machine_fingerprint()
        if not settings.trusted_host_fingerprint:
            updated_at = self._now_iso()
            self._repo.set_trusted_host_fingerprint(current_fingerprint, updated_at)
            self._log_event(
                entity_type="deployment",
                entity_id="deployment_settings",
                actor_type="system",
                actor_id="system",
                event_type="TRUSTED_HOST_BOUND",
                payload={"trusted_host_fingerprint": current_fingerprint},
                created_at=updated_at,
            )
            settings = self._repo.get()
            if settings is None:
                raise DeploymentSettingsError("Trusted host binding failed")
        return settings

    def resolve_access_profile(self, request_host: str) -> AccessProfile:
        settings = self.ensure_initialized()
        is_host_request = self.is_host_request(request_host, settings)
        return AccessProfile(
            request_machine_type="host_machine" if is_host_request else "client_machine",
            admin_visible=is_host_request,
            student_visible=True,
            deployment_profile=settings.deployment_profile,
            branding_profile=settings.branding_profile,
        )

    def is_host_request(
        self,
        request_host: str,
        settings: DeploymentSettings | None = None,
    ) -> bool:
        active_settings = settings or self.ensure_initialized()
        current_fingerprint = self.current_machine_fingerprint()
        if active_settings.trusted_host_fingerprint != current_fingerprint:
            return False
        return request_host in self.local_ip_addresses()

    def current_machine_fingerprint(self) -> str:
        machine_guid = self._read_machine_guid()
        hostname = socket.gethostname().strip().lower()
        mac_value = f"{uuid.getnode():012x}"
        raw = "|".join(part for part in [machine_guid, hostname, mac_value] if part)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def local_ip_addresses(self) -> set[str]:
        addresses = {"127.0.0.1", "::1", "localhost", "testclient", "testserver"}
        try:
            addresses.add(socket.gethostbyname(socket.gethostname()))
        except OSError:
            pass
        try:
            for item in socket.getaddrinfo(socket.gethostname(), None):
                if item[4]:
                    addresses.add(item[4][0])
        except OSError:
            pass
        return {item for item in addresses if item}

    def _read_machine_guid(self) -> str:
        if winreg is None:  # pragma: no cover
            return "non_windows_machine_guid"
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            )
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value).strip().lower()
        except OSError:  # pragma: no cover
            return "missing_machine_guid"

    def _log_event(self, **kwargs) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.log_event(**kwargs)
        except Exception:
            return

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
