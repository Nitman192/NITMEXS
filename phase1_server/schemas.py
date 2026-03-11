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
    difficulty_level: conint(ge=1, le=10) | None = None
    discrimination_index: confloat(ge=0, le=1) | None = None
    topic_tag: str | None = Field(default=None, min_length=1, max_length=120)
    cognitive_level: str | None = Field(default=None, min_length=1, max_length=80)
    options: list[OptionCreateSchema] = Field(min_length=2, max_length=6)


class QuestionMetadataUpdateSchema(BaseModel):
    difficulty: str | None = Field(default=None, min_length=1, max_length=30)
    difficulty_level: conint(ge=1, le=10) | None = None
    discrimination_index: confloat(ge=0, le=1) | None = None
    topic_tag: str | None = Field(default=None, min_length=1, max_length=120)
    cognitive_level: str | None = Field(default=None, min_length=1, max_length=80)


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
    selected_option_id: str = Field(min_length=1)
    confidence_tag: Literal["sure", "maybe", "guess"] | None = None


class StudentRegisterSchema(BaseModel):
    student_id: str = Field(min_length=3, max_length=40)
    display_name: str | None = Field(default=None, max_length=120)


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


class ExamControlSchema(BaseModel):
    reason: str | None = Field(default=None, max_length=300)
