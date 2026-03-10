"""Admin routes for question and exam management."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Header,
    Request,
    UploadFile,
    status,
)

from phase1_server.api.deps import admin_only
from phase1_server.schemas import (
    AddQuestionsSchema,
    ExamCreateSchema,
    QuestionCreateSchema,
)
from phase1_server.services.analytics_service import AnalyticsService
from phase1_server.services.audit_service import AuditService
from phase1_server.services.exam_service import (
    ExamAlreadyPublishedError,
    ExamNotFoundError,
    ExamService,
    ExamCreatePayload,
    ExamValidationError,
)
from phase1_server.services.metrics_service import MetricsService
from phase1_server.services.question_import_service import (
    CsvImportError,
    QuestionCsvImportService,
)
from phase1_server.services.question_service import (
    QuestionNotFoundError,
    QuestionService,
    QuestionCreatePayload,
    QuestionValidationError,
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
                    options=[
                        (option.option_text, option.is_correct)
                        for option in payload.options
                    ],
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


@router.post("/questions/import-csv")
async def import_questions_csv(
    request: Request,
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = (await file.read()).decode("utf-8", errors="replace")

    db = request.app.state.db
    with UnitOfWork(db) as uow:
        question_service = QuestionService(uow.questions)
        import_service = QuestionCsvImportService(question_service)
        try:
            result = import_service.import_csv(content)
        except CsvImportError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "data": {
            "total_rows": result.total_rows,
            "inserted": result.inserted,
            "failed": result.failed,
            "errors": [
                {"row": item.row, "error": item.error}
                for item in result.errors
            ],
        },
    }


@router.post("/exams", status_code=status.HTTP_201_CREATED)
def create_exam(payload: ExamCreateSchema, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
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
            "status": exam.status.value,
            "published": exam.published,
            "created_at": exam.created_at,
        },
    }


@router.post("/exams/{exam_id}/add-questions")
def add_questions(exam_id: str, payload: AddQuestionsSchema, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
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
        service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
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
            "status": exam.status.value,
            "published": exam.published,
        },
    }


@router.post("/exams/{exam_id}/close")
def close_exam(
    exam_id: str,
    request: Request,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
        try:
            exam = service.close_exam(exam_id, actor_id=x_admin_id, actor_role="admin")
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ExamValidationError, ExamAlreadyPublishedError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "data": {
            "id": exam.id,
            "name": exam.name,
            "status": exam.status.value,
            "published": exam.published,
        },
    }


@router.get("/exams")
def list_exams(request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
        exams = service.list_exams()

    return {
        "status": "success",
        "data": [
            {
                "id": exam.id,
                "name": exam.name,
                "duration_minutes": exam.duration_minutes,
                "negative_marking": exam.negative_marking,
                "status": exam.status.value,
                "published": exam.published,
                "created_at": exam.created_at,
            }
            for exam in exams
        ],
    }


@router.get("/exams/{exam_id}/analytics")
def get_exam_analytics(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = AnalyticsService(uow.analytics, uow.exams)
        try:
            analytics = service.get_exam_analytics(exam_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "success", "data": analytics}


@router.get("/attempts/{attempt_id}/timeline")
def get_attempt_timeline(attempt_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = AuditService(uow.audit_events)
        timeline = service.list_entity_timeline(entity_type="attempt", entity_id=attempt_id)

    return {"status": "success", "data": timeline}


@router.get("/system/metrics")
def get_system_metrics(request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        data = MetricsService(uow.metrics).get_metrics()

    return {"status": "success", "data": data}


@router.get("/students/{student_id}/performance")
def get_student_performance(student_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = AnalyticsService(uow.analytics, uow.exams)
        performance = service.get_student_performance(student_id)

    return {"status": "success", "data": performance}
