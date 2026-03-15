"""Business logic for bulk CSV question import."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO

from phase1_server.services.exam_service import (
    ExamCreatePayload,
    ExamService,
)
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


@dataclass(frozen=True)
class CsvExamPackageImportResult:
    exam_id: str
    exam_name: str
    duration_minutes: int
    negative_marking: float
    published: bool
    total_rows: int
    inserted: int
    failed: int
    question_ids: list[str]
    errors: list[CsvImportRowError]


class QuestionCsvImportService:
    LEGACY_REQUIRED_COLUMNS = [
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
    SIMPLIFIED_LEGACY_REQUIRED_COLUMNS = [
        "text",
        "topic",
        "marks",
        "option_a",
        "option_b",
        "correct_option",
    ]
    SIMPLIFIED_REQUIRED_COLUMNS = [
        "text",
        "topic",
        "marks",
        "question_type",
    ]
    OPTIONAL_COLUMNS = [
        "difficulty",
        "accepted_answers",
        "word_target_min",
        "word_target_max",
        "word_hard_max",
        "option_a",
        "option_b",
        "option_c",
        "option_d",
        "correct_option",
        "difficulty_level",
        "discrimination_index",
        "topic_tag",
        "cognitive_level",
    ]

    def __init__(self, question_service: QuestionService):
        self._question_service = question_service

    def import_csv(
        self,
        content: str,
        owner_admin_id: str = "superadmin",
        created_by: str = "admin",
    ) -> CsvImportResult:
        if not content.strip():
            raise CsvImportError("CSV file is empty")

        reader = csv.DictReader(StringIO(content))
        if not reader.fieldnames:
            raise CsvImportError("CSV header is missing")

        format_name = self.detect_format(reader.fieldnames)
        if format_name is None:
            raise CsvImportError(
                "CSV header not recognized. Use legacy MCQ columns or simplified Army columns "
                "(text, topic, marks, question_type, plus type-specific fields)."
            )

        errors: list[CsvImportRowError] = []
        inserted = 0
        total_rows = 0

        for row_number, row in enumerate(reader, start=2):
            if self._is_blank_row(row):
                continue
            total_rows += 1
            try:
                payload = self._parse_row(
                    row,
                    format_name=format_name,
                    owner_admin_id=owner_admin_id,
                    created_by=created_by,
                )
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

    @classmethod
    def detect_format(cls, fieldnames: list[str]) -> str | None:
        names = set(fieldnames)
        if all(column in names for column in cls.LEGACY_REQUIRED_COLUMNS):
            return "legacy"
        if all(column in names for column in cls.SIMPLIFIED_LEGACY_REQUIRED_COLUMNS):
            return "simplified"
        if all(column in names for column in cls.SIMPLIFIED_REQUIRED_COLUMNS):
            return "simplified"
        return None

    def _parse_row(
        self,
        row: dict[str, str],
        format_name: str,
        owner_admin_id: str,
        created_by: str,
    ) -> QuestionCreatePayload:
        text = (row.get("text") or "").strip()
        topic = (row.get("topic") or "").strip()
        difficulty = (row.get("difficulty") or "").strip() or "medium"
        marks_raw = (row.get("marks") or "").strip()
        difficulty_level_raw = (row.get("difficulty_level") or "").strip()
        discrimination_raw = (row.get("discrimination_index") or "").strip()
        topic_tag = (row.get("topic_tag") or "").strip() or None
        cognitive_level = (row.get("cognitive_level") or "").strip() or None
        question_type = (row.get("question_type") or "").strip() or "mcq_single"
        accepted_answers = self._parse_accepted_answers(row.get("accepted_answers"))
        word_target_min = self._parse_optional_int(
            (row.get("word_target_min") or "").strip(),
            field_name="word_target_min",
        )
        word_target_max = self._parse_optional_int(
            (row.get("word_target_max") or "").strip(),
            field_name="word_target_max",
        )
        word_hard_max = self._parse_optional_int(
            (row.get("word_hard_max") or "").strip(),
            field_name="word_hard_max",
        )

        if not text:
            raise CsvImportError("Question text cannot be empty")
        if not topic:
            raise CsvImportError("topic cannot be empty")
        if not difficulty:
            raise CsvImportError("difficulty must be string")

        try:
            marks = int(marks_raw)
        except ValueError as exc:
            raise CsvImportError("marks must be integer") from exc

        difficulty_level: int | None = None
        if difficulty_level_raw:
            try:
                difficulty_level = int(difficulty_level_raw)
            except ValueError as exc:
                raise CsvImportError("difficulty_level must be integer") from exc
            if difficulty_level < 1 or difficulty_level > 10:
                raise CsvImportError("difficulty_level must be between 1 and 10")

        discrimination_index: float | None = None
        if discrimination_raw:
            try:
                discrimination_index = float(discrimination_raw)
            except ValueError as exc:
                raise CsvImportError("discrimination_index must be numeric") from exc
            if discrimination_index < 0 or discrimination_index > 1:
                raise CsvImportError("discrimination_index must be between 0 and 1")

        options = self._parse_options(row, format_name=format_name)

        return QuestionCreatePayload(
            text=text,
            topic=topic,
            difficulty=difficulty,
            marks=marks,
            owner_admin_id=owner_admin_id,
            created_by=created_by,
            question_type=question_type,
            options=options,
            accepted_answers=accepted_answers,
            difficulty_level=difficulty_level,
            discrimination_index=discrimination_index,
            topic_tag=topic_tag,
            cognitive_level=cognitive_level,
            word_target_min=word_target_min,
            word_target_max=word_target_max,
            word_hard_max=word_hard_max,
        )

    def _parse_options(self, row: dict[str, str], format_name: str) -> list[tuple[str, bool]]:
        question_type = (row.get("question_type") or "").strip() or "mcq_single"
        if question_type == "true_false":
            correct_option = (row.get("correct_option") or "").strip().upper()
            if correct_option not in {"TRUE", "FALSE", "T", "F"}:
                raise CsvImportError("true_false questions require correct_option TRUE or FALSE")
            return [(correct_option.title(), True)]
        if question_type in {"fib_text", "short_answer", "long_answer"}:
            return []
        if format_name == "legacy":
            return self._parse_legacy_options(row)
        if format_name == "simplified":
            return self._parse_simplified_options(row)
        raise CsvImportError("Unsupported CSV format")

    def _parse_legacy_options(self, row: dict[str, str]) -> list[tuple[str, bool]]:
        options: list[tuple[str, bool]] = []
        for index in range(1, 5):
            option_text = (row.get(f"option{index}") or "").strip()
            if not option_text:
                continue
            is_correct = self._parse_bool(row.get(f"option{index}_is_correct"))
            options.append((option_text, is_correct))
        return options

    def _parse_simplified_options(self, row: dict[str, str]) -> list[tuple[str, bool]]:
        option_entries = [
            ("A", (row.get("option_a") or "").strip()),
            ("B", (row.get("option_b") or "").strip()),
            ("C", (row.get("option_c") or "").strip()),
            ("D", (row.get("option_d") or "").strip()),
        ]
        provided_entries = [
            (label, text)
            for label, text in option_entries
            if text
        ]
        if len(provided_entries) < 2:
            raise CsvImportError("At least two options are required")

        correct_option = (row.get("correct_option") or "").strip().upper()
        valid_labels = {label for label, _ in provided_entries}
        if correct_option not in valid_labels:
            raise CsvImportError("correct_option must match provided option labels (A/B/C/D)")

        return [
            (text, label == correct_option)
            for label, text in provided_entries
        ]

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

    @staticmethod
    def _parse_accepted_answers(value: str | None) -> list[str]:
        raw = (value or "").strip()
        if not raw:
            return []
        return [item.strip() for item in raw.split("|") if item.strip()]

    @staticmethod
    def _parse_optional_int(value: str, field_name: str) -> int | None:
        if not value:
            return None
        try:
            return int(value)
        except ValueError as exc:
            raise CsvImportError(f"{field_name} must be integer") from exc


class ExamQuestionPackageCsvImportService:
    REQUIRED_EXAM_COLUMNS = [
        "exam_name",
        "duration_minutes",
        "negative_marking",
    ]
    OPTIONAL_EXAM_COLUMNS = [
        "publish_exam",
    ]

    def __init__(
        self,
        question_service: QuestionService,
        exam_service: ExamService,
    ):
        self._question_service = question_service
        self._exam_service = exam_service

    def import_csv(
        self,
        content: str,
        owner_admin_id: str = "superadmin",
        created_by: str = "admin",
    ) -> CsvExamPackageImportResult:
        if not content.strip():
            raise CsvImportError("CSV file is empty")

        reader = csv.DictReader(StringIO(content))
        if not reader.fieldnames:
            raise CsvImportError("CSV header is missing")

        missing_exam_columns = [
            col for col in self.REQUIRED_EXAM_COLUMNS if col not in reader.fieldnames
        ]
        if missing_exam_columns:
            raise CsvImportError(f"Missing required columns: {', '.join(missing_exam_columns)}")

        parser = QuestionCsvImportService(self._question_service)
        question_format = parser.detect_format(reader.fieldnames)
        if question_format is None:
            raise CsvImportError(
                "CSV header not recognized. Use legacy columns "
                "(option1..option4 + option*_is_correct) or simplified columns "
                "(option_a..option_d + correct_option)."
            )
        errors: list[CsvImportRowError] = []
        inserted = 0
        total_rows = 0
        created_question_ids: list[str] = []

        exam_name = ""
        duration_minutes = 0
        negative_marking = 0.0
        publish_requested = False
        exam_id = ""

        for row_number, row in enumerate(reader, start=2):
            if parser._is_blank_row(row):
                continue

            total_rows += 1
            if not exam_id:
                exam_name = (row.get("exam_name") or "").strip()
                if not exam_name:
                    raise CsvImportError("exam_name cannot be empty")
                duration_minutes = self._parse_duration_minutes(
                    (row.get("duration_minutes") or "").strip()
                )
                negative_marking = self._parse_negative_marking(
                    (row.get("negative_marking") or "").strip()
                )
                publish_requested = self._parse_optional_bool(
                    row.get("publish_exam"),
                    default=False,
                )
                exam = self._exam_service.create_exam(
                    ExamCreatePayload(
                        name=exam_name,
                        duration_minutes=duration_minutes,
                        negative_marking=negative_marking,
                        owner_admin_id=owner_admin_id,
                    )
                )
                exam_id = exam.id
            else:
                row_exam_name = (row.get("exam_name") or "").strip()
                if row_exam_name and row_exam_name != exam_name:
                    errors.append(
                        CsvImportRowError(
                            row=row_number,
                            error="exam_name must match first row exam_name",
                        )
                    )
                    continue

            try:
                payload = parser._parse_row(
                    row,
                    format_name=question_format,
                    owner_admin_id=owner_admin_id,
                    created_by=created_by,
                )
                question = self._question_service.create_question(payload)
                created_question_ids.append(question.id)
                inserted += 1
            except (CsvImportError, QuestionValidationError, ValueError) as exc:
                errors.append(CsvImportRowError(row=row_number, error=str(exc)))

        if total_rows == 0:
            raise CsvImportError("CSV contains no data rows")
        if not exam_id:
            raise CsvImportError("Unable to initialize exam from CSV")

        if created_question_ids:
            self._exam_service.add_questions(exam_id, created_question_ids)

        published = False
        if publish_requested and created_question_ids:
            self._exam_service.publish_exam(exam_id)
            published = True
        elif publish_requested and not created_question_ids:
            errors.append(
                CsvImportRowError(
                    row=0,
                    error="publish_exam requested but no valid questions were imported",
                )
            )

        return CsvExamPackageImportResult(
            exam_id=exam_id,
            exam_name=exam_name,
            duration_minutes=duration_minutes,
            negative_marking=negative_marking,
            published=published,
            total_rows=total_rows,
            inserted=inserted,
            failed=len(errors),
            question_ids=created_question_ids,
            errors=errors,
        )

    @staticmethod
    def _parse_duration_minutes(value: str) -> int:
        try:
            duration = int(value)
        except ValueError as exc:
            raise CsvImportError("duration_minutes must be integer") from exc
        if duration <= 0:
            raise CsvImportError("duration_minutes must be > 0")
        return duration

    @staticmethod
    def _parse_negative_marking(value: str) -> float:
        try:
            negative = float(value)
        except ValueError as exc:
            raise CsvImportError("negative_marking must be numeric") from exc
        if negative < 0:
            raise CsvImportError("negative_marking must be >= 0")
        return negative

    @staticmethod
    def _parse_optional_bool(value: str | None, default: bool) -> bool:
        normalized = (value or "").strip().lower()
        if not normalized:
            return default
        if normalized in {"1", "true", "yes"}:
            return True
        if normalized in {"0", "false", "no"}:
            return False
        raise CsvImportError("publish_exam must be boolean")
