"""Business logic for bulk CSV question import."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO

from phase1_server.services.question_service import (
    QuestionCreatePayload,
    QuestionService,
    QuestionValidationError,
)


class CsvImportError(ValueError):
    pass


@dataclass(frozen=True)
class CsvImportRowError:
    row: int
    error: str


@dataclass(frozen=True)
class CsvImportResult:
    total_rows: int
    inserted: int
    failed: int
    errors: list[CsvImportRowError]


class QuestionCsvImportService:
    REQUIRED_COLUMNS = [
        "text",
        "topic",
        "difficulty",
        "marks",
        "option1",
        "option1_is_correct",
        "option2",
        "option2_is_correct",
        "option3",
        "option3_is_correct",
        "option4",
        "option4_is_correct",
    ]

    def __init__(self, question_service: QuestionService):
        self._question_service = question_service

    def import_csv(self, content: str) -> CsvImportResult:
        if not content.strip():
            raise CsvImportError("CSV file is empty")

        reader = csv.DictReader(StringIO(content))
        if not reader.fieldnames:
            raise CsvImportError("CSV header is missing")

        missing = [col for col in self.REQUIRED_COLUMNS if col not in reader.fieldnames]
        if missing:
            raise CsvImportError(f"Missing required columns: {', '.join(missing)}")

        errors: list[CsvImportRowError] = []
        inserted = 0
        total_rows = 0

        for row_number, row in enumerate(reader, start=2):
            if self._is_blank_row(row):
                continue
            total_rows += 1
            try:
                payload = self._parse_row(row)
                self._question_service.create_question(payload)
                inserted += 1
            except (CsvImportError, QuestionValidationError, ValueError) as exc:
                errors.append(CsvImportRowError(row=row_number, error=str(exc)))

        return CsvImportResult(
            total_rows=total_rows,
            inserted=inserted,
            failed=len(errors),
            errors=errors,
        )

    def _parse_row(self, row: dict[str, str]) -> QuestionCreatePayload:
        text = (row.get("text") or "").strip()
        topic = (row.get("topic") or "").strip()
        difficulty = (row.get("difficulty") or "").strip()
        marks_raw = (row.get("marks") or "").strip()

        if not text:
            raise CsvImportError("Question text cannot be empty")
        if not difficulty:
            raise CsvImportError("difficulty must be string")

        try:
            marks = int(marks_raw)
        except ValueError as exc:
            raise CsvImportError("marks must be integer") from exc

        options: list[tuple[str, bool]] = []
        for index in range(1, 5):
            option_text = (row.get(f"option{index}") or "").strip()
            if not option_text:
                continue
            is_correct = self._parse_bool(row.get(f"option{index}_is_correct"))
            options.append((option_text, is_correct))

        if len(options) < 2:
            raise CsvImportError("At least two options are required")

        return QuestionCreatePayload(
            text=text,
            topic=topic,
            difficulty=difficulty,
            marks=marks,
            options=options,
        )

    @staticmethod
    def _parse_bool(value: str | None) -> bool:
        normalized = (value or "").strip().lower()
        if normalized in {"1", "true", "yes"}:
            return True
        if normalized in {"0", "false", "no", ""}:
            return False
        raise CsvImportError("option_is_correct must be boolean")

    @staticmethod
    def _is_blank_row(row: dict[str, str]) -> bool:
        return all(not (value or "").strip() for value in row.values())
