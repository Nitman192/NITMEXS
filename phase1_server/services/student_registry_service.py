"""Business rules for managed student login IDs."""

from __future__ import annotations

import hashlib
import secrets
import re
from dataclasses import dataclass

from phase1_server.models import utc_now_iso
from phase1_server.repositories.student_registry_repository import StudentRegistryRepository


class StudentRegistryError(ValueError):
    pass


class StudentValidationError(StudentRegistryError):
    pass


class StudentAlreadyExistsError(StudentRegistryError):
    pass


@dataclass(frozen=True)
class StudentRegisterPayload:
    student_id: str
    display_name: str | None
    created_by: str
    password: str | None = None


@dataclass(frozen=True)
class StudentGeneratePayload:
    prefix: str
    count: int
    created_by: str


class StudentRegistryService:
    _STUDENT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{3,40}$")
    _PREFIX_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{2,20}$")

    def __init__(self, repo: StudentRegistryRepository):
        self._repo = repo

    def register_student(self, payload: StudentRegisterPayload) -> dict:
        student_id = self._normalize_student_id(payload.student_id)
        display_name = self._normalize_display_name(payload.display_name)
        created_by = (payload.created_by or "admin").strip() or "admin"
        password = self._normalize_password(student_id, payload.password)

        if self._repo.exists(student_id):
            raise StudentAlreadyExistsError(f"Student ID '{student_id}' already exists")

        created_at = utc_now_iso()
        self._repo.create_student(
            student_id=student_id,
            display_name=display_name,
            password_hash=self._hash_password(student_id, password),
            created_by=created_by,
            owner_admin_id=created_by,
            created_at=created_at,
        )
        return {
            "student_id": student_id,
            "display_name": display_name,
            "created_by": created_by,
            "owner_admin_id": created_by,
            "password": password,
            "created_at": created_at,
            "status": "ACTIVE",
        }

    def generate_students(self, payload: StudentGeneratePayload) -> dict:
        prefix = self._normalize_prefix(payload.prefix)
        count = int(payload.count)
        created_by = (payload.created_by or "admin").strip() or "admin"
        if count < 1 or count > 200:
            raise StudentValidationError("count must be between 1 and 200")

        generated: list[dict] = []
        sequence = 1
        safety_limit = 100000

        while len(generated) < count and sequence <= safety_limit:
            candidate_id = f"{prefix}-{sequence:03d}"
            sequence += 1
            if self._repo.exists(candidate_id):
                continue
            created_at = utc_now_iso()
            password = self._generate_password()
            self._repo.create_student(
                student_id=candidate_id,
                display_name=None,
                password_hash=self._hash_password(candidate_id, password),
                created_by=created_by,
                owner_admin_id=created_by,
                created_at=created_at,
            )
            generated.append(
                {
                    "student_id": candidate_id,
                    "display_name": None,
                    "created_by": created_by,
                    "owner_admin_id": created_by,
                    "password": password,
                    "created_at": created_at,
                    "status": "ACTIVE",
                }
            )

        if len(generated) < count:
            raise StudentValidationError("Unable to generate enough unique student IDs")

        return {
            "prefix": prefix,
            "generated_count": len(generated),
            "students": generated,
        }

    def list_students(
        self,
        limit: int = 300,
        owner_admin_id: str | None = None,
        include_all: bool = False,
    ) -> list[dict]:
        normalized_limit = max(1, min(int(limit), 1000))
        return self._repo.list_students(
            limit=normalized_limit,
            owner_admin_id=owner_admin_id,
            include_all=include_all,
        )

    def authenticate_student(self, student_id: str, password: str) -> dict:
        normalized_student_id = self._normalize_student_id(student_id)
        normalized_password = self._normalize_password(normalized_student_id, password)
        record = self._repo.get_student_auth_record(normalized_student_id)
        if record is None or record.get("status") != "ACTIVE":
            raise StudentValidationError("Invalid student credentials")
        expected_hash = record.get("password_hash") or ""
        if expected_hash != self._hash_password(normalized_student_id, normalized_password):
            raise StudentValidationError("Invalid student credentials")
        return {
            "student_id": record["student_id"],
            "display_name": record.get("display_name"),
            "status": record.get("status"),
            "owner_admin_id": record.get("owner_admin_id"),
        }

    def _normalize_student_id(self, student_id: str) -> str:
        value = (student_id or "").strip()
        if not self._STUDENT_ID_PATTERN.match(value):
            raise StudentValidationError(
                "student_id must be 3-40 chars and only letters, digits, ., _, -"
            )
        return value

    def _normalize_prefix(self, prefix: str) -> str:
        value = (prefix or "").strip()
        if not self._PREFIX_PATTERN.match(value):
            raise StudentValidationError(
                "prefix must be 2-20 chars and only letters, digits, ., _, -"
            )
        return value

    @staticmethod
    def _normalize_display_name(display_name: str | None) -> str | None:
        if display_name is None:
            return None
        value = display_name.strip()
        if not value:
            return None
        if len(value) > 120:
            raise StudentValidationError("display_name must be <= 120 characters")
        return value

    @staticmethod
    def _normalize_password(student_id: str, password: str | None) -> str:
        value = (password or "").strip()
        if not value:
            value = student_id
        if len(value) < 4 or len(value) > 120:
            raise StudentValidationError("password must be between 4 and 120 characters")
        return value

    @staticmethod
    def _hash_password(student_id: str, password: str) -> str:
        return hashlib.sha256(f"{student_id}:{password}".encode("utf-8")).hexdigest()

    @staticmethod
    def _generate_password(length: int = 8) -> str:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
        return "".join(secrets.choice(alphabet) for _ in range(length))
