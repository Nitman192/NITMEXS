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


class ExamStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class QuestionType(str, Enum):
    MCQ_SINGLE = "mcq_single"
    TRUE_FALSE = "true_false"
    FIB_TEXT = "fib_text"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"


class QuestionVariantDecision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class AdminRole(str, Enum):
    SUPERADMIN = "superadmin"
    EXAMINER = "examiner"


class GradingState(str, Enum):
    AUTO_CORRECT = "auto_correct"
    AUTO_INCORRECT = "auto_incorrect"
    PENDING_REVIEW = "pending_review"
    REVIEW_RESOLVED = "review_resolved"


@dataclass
class Attempt:
    id: str
    candidate_id: str
    exam_id: str
    status: AttemptStatus
    created_at: str
    updated_at: str
    version: int = 0
    submitted_at: str | None = None
    expires_at: str | None = None
    timer_frozen: bool = False
    timer_paused_at: str | None = None


@dataclass
class Question:
    id: str
    text: str
    topic: str
    difficulty: str
    marks: float
    created_at: str
    owner_admin_id: str = "superadmin"
    question_type: QuestionType = QuestionType.MCQ_SINGLE
    difficulty_level: int | None = None
    discrimination_index: float | None = None
    topic_tag: str | None = None
    cognitive_level: str | None = None
    word_target_min: int | None = None
    word_target_max: int | None = None
    word_hard_max: int | None = None


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
    status: ExamStatus
    published: bool
    created_at: str
    owner_admin_id: str = "superadmin"
    passing_percentage: float = 40.0
    reference_exam_id: str | None = None
    custom_rules: list[str] | None = None
    results_published: bool = False
    results_published_at: str | None = None
    results_published_by: str | None = None


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
    selected_option_id: str | None
    text_answer: str | None
    normalized_text_answer: str | None
    word_count: int | None
    answered_at: str


@dataclass
class QuestionTextVariant:
    id: str
    question_id: str
    answer_text: str
    normalized_answer_text: str
    decision: QuestionVariantDecision
    created_by: str
    created_at: str


@dataclass
class DeploymentSettings:
    id: int
    deployment_profile: str
    branding_profile: str
    student_result_policy: str
    trusted_host_fingerprint: str | None
    created_at: str
    updated_at: str


@dataclass
class AdminAccount:
    admin_id: str
    display_name: str | None
    role: AdminRole
    access_key_hash: str
    status: str
    created_by: str
    created_at: str


@dataclass
class ResultArtifact:
    id: str
    artifact_type: str
    entity_type: str
    entity_id: str
    created_by: str
    file_name: str
    content_type: str
    checksum: str
    reference_code: str
    created_at: str


@dataclass(frozen=True)
class AdminIdentity:
    admin_id: str
    role: AdminRole
    display_name: str | None = None

    @property
    def is_superadmin(self) -> bool:
        return self.role is AdminRole.SUPERADMIN


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
