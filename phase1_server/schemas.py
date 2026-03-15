"""Pydantic request/response schemas for APIs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, conint, confloat


class OptionCreateSchema(BaseModel):
    option_text: str = Field(min_length=1, max_length=500)
    is_correct: bool


class QuestionCreateSchema(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    topic: str = Field(min_length=1, max_length=120)
    difficulty: str = Field(min_length=1, max_length=30)
    marks: confloat(gt=0)
    question_type: Literal["mcq_single", "true_false", "fib_text", "short_answer", "long_answer"] = "mcq_single"
    difficulty_level: conint(ge=1, le=10) | None = None
    discrimination_index: confloat(ge=0, le=1) | None = None
    topic_tag: str | None = Field(default=None, min_length=1, max_length=120)
    cognitive_level: str | None = Field(default=None, min_length=1, max_length=80)
    options: list[OptionCreateSchema] | None = Field(default=None, max_length=6)
    accepted_answers: list[str] | None = Field(default=None, max_length=20)
    word_target_min: conint(ge=1, le=5000) | None = None
    word_target_max: conint(ge=1, le=5000) | None = None
    word_hard_max: conint(ge=1, le=10000) | None = None


class QuestionMetadataUpdateSchema(BaseModel):
    difficulty: str | None = Field(default=None, min_length=1, max_length=30)
    difficulty_level: conint(ge=1, le=10) | None = None
    discrimination_index: confloat(ge=0, le=1) | None = None
    topic_tag: str | None = Field(default=None, min_length=1, max_length=120)
    cognitive_level: str | None = Field(default=None, min_length=1, max_length=80)
    word_target_min: conint(ge=1, le=5000) | None = None
    word_target_max: conint(ge=1, le=5000) | None = None
    word_hard_max: conint(ge=1, le=10000) | None = None


class QuestionRecalibrationSchema(BaseModel):
    min_attempts: conint(ge=1, le=1000) = 5
    apply: bool = False


class QuestionRecalibrationRollbackSchema(BaseModel):
    reason: str | None = Field(default=None, max_length=400)


class ProctorAlertResolveSchema(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class ExamCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    duration_minutes: conint(gt=0, le=480)
    negative_marking: confloat(ge=0)


class AddQuestionsSchema(BaseModel):
    question_ids: list[str] = Field(min_length=1)


class AnswerSubmitSchema(BaseModel):
    question_id: str = Field(min_length=1)
    selected_option_id: str | None = Field(default=None, min_length=1)
    text_answer: str | None = Field(default=None, max_length=20000)


class StudentRegisterSchema(BaseModel):
    student_id: str = Field(min_length=3, max_length=40)
    display_name: str | None = Field(default=None, max_length=120)
    password: str | None = Field(default=None, min_length=4, max_length=120)


class StudentGenerateSchema(BaseModel):
    prefix: str = Field(default="cadet", min_length=2, max_length=20)
    count: conint(ge=1, le=200) = 10


class ForceSubmitSchema(BaseModel):
    reason: str | None = Field(default=None, max_length=400)


class StudentIssueReportSchema(BaseModel):
    question_id: str = Field(min_length=1)
    issue_type: str = Field(default="content_issue", min_length=2, max_length=80)
    note: str | None = Field(default=None, max_length=600)


class TechnicalIssueReportSchema(BaseModel):
    issue_type: str = Field(default="technical_issue", min_length=2, max_length=80)
    note: str | None = Field(default=None, max_length=600)


class AdminBroadcastSchema(BaseModel):
    message: str = Field(min_length=3, max_length=600)
    severity: Literal["info", "warn", "critical"] = "info"


class BroadcastReceiptSchema(BaseModel):
    broadcast_ids: list[str] = Field(min_length=1, max_length=50)
    received_at: str | None = None


class ExamControlSchema(BaseModel):
    reason: str | None = Field(default=None, max_length=300)
    freeze_timer: bool = False


class StudentLoginSchema(BaseModel):
    student_id: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=4, max_length=120)


class AdminLoginSchema(BaseModel):
    admin_id: str = Field(min_length=3, max_length=40)
    access_key: str = Field(min_length=4, max_length=120)


class AdminAccountCreateSchema(BaseModel):
    admin_id: str = Field(min_length=3, max_length=40)
    display_name: str | None = Field(default=None, max_length=120)
    role: Literal["superadmin", "examiner"] = "examiner"
    access_key: str = Field(min_length=4, max_length=120)


class ExamRulesUpdateSchema(BaseModel):
    custom_rules: list[str] = Field(default_factory=list, max_length=20)


class AIExplainRequestSchema(BaseModel):
    question_id: str = Field(min_length=1)


class ExamReferenceUpdateSchema(BaseModel):
    reference_exam_id: str | None = Field(default=None, min_length=1)


class FibReviewDecisionSchema(BaseModel):
    question_id: str = Field(min_length=1)
    normalized_text_answer: str = Field(min_length=1, max_length=4000)
    decision: Literal["accepted", "rejected"]
    canonical_answer_text: str = Field(min_length=1, max_length=4000)


class SubjectiveReviewSchema(BaseModel):
    question_id: str = Field(min_length=1)
    marks_awarded: confloat(ge=0)
    review_note: str | None = Field(default=None, max_length=1000)
