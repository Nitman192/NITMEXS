"""Business rules for superadmin and examiner account management."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from phase1_server.models import AdminAccount, AdminIdentity, AdminRole, utc_now_iso
from phase1_server.repositories.admin_account_repository import AdminAccountRepository


class AdminAccountError(ValueError):
    pass


class AdminAuthenticationError(AdminAccountError):
    pass


class AdminAuthorizationError(AdminAccountError):
    pass


class AdminValidationError(AdminAccountError):
    pass


@dataclass(frozen=True)
class AdminAccountCreatePayload:
    admin_id: str
    display_name: str | None
    role: str
    access_key: str
    created_by: str


class AdminAccountService:
    def __init__(self, repo: AdminAccountRepository):
        self._repo = repo

    def authenticate(self, admin_id: str, access_key: str) -> AdminIdentity:
        normalized_admin_id = self._normalize_admin_id(admin_id)
        normalized_key = self._normalize_access_key(access_key)
        account = self._repo.get_account(normalized_admin_id)
        if account is None or account.status != "ACTIVE":
            raise AdminAuthenticationError("Invalid admin credentials")
        if account.access_key_hash != self._hash_access_key(normalized_admin_id, normalized_key):
            raise AdminAuthenticationError("Invalid admin credentials")
        return AdminIdentity(
            admin_id=account.admin_id,
            role=account.role,
            display_name=account.display_name,
        )

    def resolve_identity(self, admin_id: str | None) -> AdminIdentity:
        normalized_admin_id = (admin_id or "").strip() or "admin"
        account = self._repo.get_account(normalized_admin_id)
        if account is None:
            return AdminIdentity(admin_id=normalized_admin_id, role=AdminRole.SUPERADMIN)
        return AdminIdentity(
            admin_id=account.admin_id,
            role=account.role,
            display_name=account.display_name,
        )

    def list_accounts(self, viewer: AdminIdentity) -> list[dict]:
        if not viewer.is_superadmin:
            raise AdminAuthorizationError("Only superadmin can view admin accounts")
        return [
            {
                "admin_id": account.admin_id,
                "display_name": account.display_name,
                "role": account.role.value,
                "status": account.status,
                "created_by": account.created_by,
                "created_at": account.created_at,
            }
            for account in self._repo.list_accounts()
        ]

    def create_account(
        self,
        payload: AdminAccountCreatePayload,
        viewer: AdminIdentity,
    ) -> dict:
        if not viewer.is_superadmin:
            raise AdminAuthorizationError("Only superadmin can create admin accounts")
        admin_id = self._normalize_admin_id(payload.admin_id)
        role = self._normalize_role(payload.role)
        access_key = self._normalize_access_key(payload.access_key)
        display_name = self._normalize_display_name(payload.display_name)
        if self._repo.get_account(admin_id) is not None:
            raise AdminValidationError(f"Admin '{admin_id}' already exists")
        account = AdminAccount(
            admin_id=admin_id,
            display_name=display_name,
            role=role,
            access_key_hash=self._hash_access_key(admin_id, access_key),
            status="ACTIVE",
            created_by=payload.created_by,
            created_at=utc_now_iso(),
        )
        self._repo.create_account(account)
        return {
            "admin_id": account.admin_id,
            "display_name": account.display_name,
            "role": account.role.value,
            "status": account.status,
            "created_by": account.created_by,
            "created_at": account.created_at,
        }

    @staticmethod
    def _normalize_admin_id(admin_id: str) -> str:
        value = (admin_id or "").strip()
        if len(value) < 3 or len(value) > 40:
            raise AdminValidationError("admin_id must be between 3 and 40 characters")
        return value

    @staticmethod
    def _normalize_display_name(display_name: str | None) -> str | None:
        if display_name is None:
            return None
        value = display_name.strip()
        if not value:
            return None
        if len(value) > 120:
            raise AdminValidationError("display_name must be <= 120 characters")
        return value

    @staticmethod
    def _normalize_role(role: str) -> AdminRole:
        normalized = (role or "").strip().lower()
        if normalized not in {AdminRole.SUPERADMIN.value, AdminRole.EXAMINER.value}:
            raise AdminValidationError("role must be superadmin or examiner")
        return AdminRole(normalized)

    @staticmethod
    def _normalize_access_key(access_key: str) -> str:
        value = (access_key or "").strip()
        if len(value) < 4 or len(value) > 120:
            raise AdminValidationError("access_key must be between 4 and 120 characters")
        return value

    @staticmethod
    def _hash_access_key(admin_id: str, access_key: str) -> str:
        return hashlib.sha256(f"{admin_id}:{access_key}".encode("utf-8")).hexdigest()
