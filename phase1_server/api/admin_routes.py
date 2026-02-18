"""Admin routes for question and exam management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from phase1_server.api.deps import admin_only
from phase1_server.schemas import AddQuestionsSchema, ExamCreateSchema, QuestionCreateSchema
from phase1_server.services.exam_service import (
    ExamAlreadyPublishedError,
    ExamNotFoundError,
    ExamService,
    ExamValidationError,
    ExamCreatePayload,
)
from phase1_server.services.question_service import (
    QuestionNotFoundError,
    QuestionService,
    QuestionValidationError,
    QuestionCreatePayload,
)
from phase1_server.uow import UnitOfWork

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_only)])


@router.post("/questions", status_code=status.HTTP_201_CREATED)
def create_question(payload: QuestionCreateSchema, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = QuestionService(uow.questions)
        try:
            question = service.create_question(
                QuestionCreatePayload(
                    text=payload.text,
                    topic=payload.topic,
                    difficulty=payload.difficulty,
                    marks=payload.marks,
                    options=[(option.option_text, option.is_correct) for option in payload.options],
                )
            )
        except QuestionValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "data": {
            "id": question.id,
            "text": question.text,
            "topic": question.topic,
            "difficulty": question.difficulty,
            "marks": question.marks,
            "created_at": question.created_at,
        },
    }


@router.get("/questions")
def list_questions(request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = QuestionService(uow.questions)
        items = service.list_questions()

    return {"status": "success", "data": items}


@router.delete("/questions/{question_id}")
def delete_question(question_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = QuestionService(uow.questions)
        try:
            service.delete_question(question_id)
        except QuestionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "success", "data": {"deleted": True, "question_id": question_id}}


@router.post("/exams", status_code=status.HTTP_201_CREATED)
def create_exam(payload: ExamCreateSchema, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = ExamService(uow.exams, uow.questions)
        try:
            exam = service.create_exam(
                ExamCreatePayload(
                    name=payload.name,
                    duration_minutes=payload.duration_minutes,
                    negative_marking=payload.negative_marking,
                )
            )
        except ExamValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "data": {
            "id": exam.id,
            "name": exam.name,
            "duration_minutes": exam.duration_minutes,
            "negative_marking": exam.negative_marking,
            "published": exam.published,
            "created_at": exam.created_at,
        },
    }


@router.post("/exams/{exam_id}/add-questions")
def add_questions(exam_id: str, payload: AddQuestionsSchema, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = ExamService(uow.exams, uow.questions)
        try:
            service.add_questions(exam_id, payload.question_ids)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ExamAlreadyPublishedError, ExamValidationError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "data": {"exam_id": exam_id, "question_ids": payload.question_ids},
    }


@router.post("/exams/{exam_id}/publish")
def publish_exam(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = ExamService(uow.exams, uow.questions)
        try:
            exam = service.publish_exam(exam_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ExamAlreadyPublishedError, ExamValidationError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "data": {
            "id": exam.id,
            "name": exam.name,
            "published": exam.published,
        },
    }


@router.get("/exams")
def list_exams(request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = ExamService(uow.exams, uow.questions)
        exams = service.list_exams()

    return {
        "status": "success",
        "data": [
            {
                "id": exam.id,
                "name": exam.name,
                "duration_minutes": exam.duration_minutes,
                "negative_marking": exam.negative_marking,
                "published": exam.published,
                "created_at": exam.created_at,
            }
            for exam in exams
        ],
    }
