"""Domain models for attempts, questions, exams, and student responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class AttemptStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    FINALIZED = "finalized"
    GRADED = "graded"
    ARCHIVED = "archived"


@dataclass
class Attempt:
    id: str
    candidate_id: str
    exam_id: str
    status: AttemptStatus
    created_at: str
    updated_at: str
    submitted_at: str | None = None


@dataclass
class Question:
    id: str
    text: str
    topic: str
    difficulty: str
    marks: float
    created_at: str


@dataclass
class Option:
    id: str
    question_id: str
    option_text: str
    is_correct: bool


@dataclass
class Exam:
    id: str
    name: str
    duration_minutes: int
    negative_marking: float
    published: bool
    created_at: str


@dataclass
class ExamQuestion:
    exam_id: str
    question_id: str


@dataclass
class AttemptQuestionSnapshot:
    attempt_id: str
    exam_id: str
    question_id: str
    order_index: int
    created_at: str


@dataclass
class AttemptResponse:
    attempt_id: str
    question_id: str
    selected_option_id: str
    answered_at: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
