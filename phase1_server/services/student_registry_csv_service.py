"""CSV import/export helpers for managed student accounts."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO

from phase1_server.services.student_registry_service import (
    StudentAlreadyExistsError,
    StudentRegisterPayload,
    StudentRegistryService,
    StudentValidationError,
)


class StudentCsvError(ValueError):
    pass


@dataclass(frozen=True)
class StudentCsvRowError:
    row: int
    error: str


@dataclass(frozen=True)
class StudentCsvImportResult:
    total_rows: int
    inserted: int
    failed: int
    errors: list[StudentCsvRowError]


class StudentRegistryCsvService:
    REQUIRED_COLUMNS = ["student_id"]
    OPTIONAL_COLUMNS = ["display_name", "created_by"]
    EXPORT_COLUMNS = ["student_id", "display_name", "status", "created_by", "created_at"]

    def __init__(self, registry_service: StudentRegistryService):
        self._registry_service = registry_service

    def import_csv(
        self,
        content: str,
        default_created_by: str = "admin",
    ) -> StudentCsvImportResult:
        if not content.strip():
            raise StudentCsvError("CSV file is empty")

        reader = csv.DictReader(StringIO(content))
        if not reader.fieldnames:
            raise StudentCsvError("CSV header is missing")

        missing = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in reader.fieldnames
        ]
        if missing:
            raise StudentCsvError(f"Missing required columns: {', '.join(missing)}")

        errors: list[StudentCsvRowError] = []
        inserted = 0
        total_rows = 0

        for row_number, row in enumerate(reader, start=2):
            if self._is_blank_row(row):
                continue

            total_rows += 1
            student_id = (row.get("student_id") or "").strip()
            display_name = (row.get("display_name") or "").strip() or None
            created_by = (row.get("created_by") or "").strip() or default_created_by

            try:
                self._registry_service.register_student(
                    StudentRegisterPayload(
                        student_id=student_id,
                        display_name=display_name,
                        created_by=created_by,
                    )
                )
                inserted += 1
            except (StudentValidationError, StudentAlreadyExistsError) as exc:
                errors.append(StudentCsvRowError(row=row_number, error=str(exc)))

        return StudentCsvImportResult(
            total_rows=total_rows,
            inserted=inserted,
            failed=len(errors),
            errors=errors,
        )

    def export_csv(self, limit: int = 1000) -> str:
        students = self._registry_service.list_students(limit=limit)
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=self.EXPORT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for student in students:
            writer.writerow(
                {
                    "student_id": student.get("student_id") or "",
                    "display_name": student.get("display_name") or "",
                    "status": student.get("status") or "ACTIVE",
                    "created_by": student.get("created_by") or "",
                    "created_at": student.get("created_at") or "",
                }
            )
        return output.getvalue()

    @staticmethod
    def _is_blank_row(row: dict[str, str]) -> bool:
        return all(not (value or "").strip() for value in row.values())
