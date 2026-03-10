"""Business rules for managed student login IDs."""

from __future__ import annotations

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

        if self._repo.exists(student_id):
            raise StudentAlreadyExistsError(f"Student ID '{student_id}' already exists")

        created_at = utc_now_iso()
        self._repo.create_student(
            student_id=student_id,
            display_name=display_name,
            created_by=created_by,
            created_at=created_at,
        )
        return {
            "student_id": student_id,
            "display_name": display_name,
            "created_by": created_by,
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
            self._repo.create_student(
                student_id=candidate_id,
                display_name=None,
                created_by=created_by,
                created_at=created_at,
            )
            generated.append(
                {
                    "student_id": candidate_id,
                    "display_name": None,
                    "created_by": created_by,
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

    def list_students(self, limit: int = 300) -> list[dict]:
        normalized_limit = max(1, min(int(limit), 1000))
        return self._repo.list_students(limit=normalized_limit)

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

