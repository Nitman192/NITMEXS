"""Pydantic request/response schemas for APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field, conint, confloat


class OptionCreateSchema(BaseModel):
    option_text: str = Field(min_length=1, max_length=500)
    is_correct: bool


class QuestionCreateSchema(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    topic: str = Field(min_length=1, max_length=120)
    difficulty: str = Field(min_length=1, max_length=30)
    marks: confloat(gt=0)
    options: list[OptionCreateSchema] = Field(min_length=2, max_length=6)


class ExamCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    duration_minutes: conint(gt=0, le=480)
    negative_marking: confloat(ge=0)


class AddQuestionsSchema(BaseModel):
    question_ids: list[str] = Field(min_length=1)


class AnswerSubmitSchema(BaseModel):
    question_id: str = Field(min_length=1)
    selected_option_id: str = Field(min_length=1)
