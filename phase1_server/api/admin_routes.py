"""Admin routes for question and exam management."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Header,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response

from phase1_server.api.deps import admin_only
from phase1_server.schemas import (
    AddQuestionsSchema,
    AdminBroadcastSchema,
    ExamCreateSchema,
    ExamControlSchema,
    ForceSubmitSchema,
    ProctorAlertResolveSchema,
    QuestionCreateSchema,
    QuestionMetadataUpdateSchema,
    QuestionRecalibrationSchema,
    QuestionRecalibrationRollbackSchema,
    StudentGenerateSchema,
    StudentRegisterSchema,
)
from phase1_server.services.analytics_service import AnalyticsService
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import (
    AttemptStateError,
    DeliveryError,
    DeliveryService,
)
from phase1_server.services.exam_service import (
    ExamAlreadyPublishedError,
    ExamNotFoundError,
    ExamService,
    ExamCreatePayload,
    ExamValidationError,
)
from phase1_server.services.metrics_service import MetricsService
from phase1_server.services.proctor_alert_service import (
    ProctorAlertNotFoundError,
    ProctorAlertService,
    ProctorAlertValidationError,
)
from phase1_server.services.proctoring_service import (
    ProctoringService,
    ProctoringValidationError,
)
from phase1_server.services.question_calibration_service import (
    QuestionCalibrationError,
    QuestionCalibrationService,
    QuestionRecalibrationRollbackRequest,
    QuestionRecalibrationRequest,
    RecalibrationRollbackError,
    RecalibrationRunNotFoundError,
)
from phase1_server.services.question_import_service import (
    CsvImportError,
    ExamQuestionPackageCsvImportService,
    QuestionCsvImportService,
)
from phase1_server.services.question_service import (
    QuestionNotFoundError,
    QuestionService,
    QuestionCreatePayload,
    QuestionMetadataUpdatePayload,
    QuestionValidationError,
)
from phase1_server.services.student_registry_service import (
    StudentAlreadyExistsError,
    StudentGeneratePayload,
    StudentRegisterPayload,
    StudentRegistryService,
    StudentValidationError,
)
from phase1_server.services.student_registry_csv_service import (
    StudentCsvError,
    StudentRegistryCsvService,
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
                    difficulty_level=payload.difficulty_level,
                    discrimination_index=payload.discrimination_index,
                    topic_tag=payload.topic_tag,
                    cognitive_level=payload.cognitive_level,
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
            "difficulty_level": question.difficulty_level,
            "discrimination_index": question.discrimination_index,
            "topic_tag": question.topic_tag,
            "cognitive_level": question.cognitive_level,
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


@router.patch("/questions/{question_id}/metadata")
def update_question_metadata(
    question_id: str,
    payload: QuestionMetadataUpdateSchema,
    request: Request,
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = QuestionService(uow.questions)
        try:
            question = service.update_question_metadata(
                question_id,
                QuestionMetadataUpdatePayload(
                    difficulty=payload.difficulty,
                    difficulty_level=payload.difficulty_level,
                    discrimination_index=payload.discrimination_index,
                    topic_tag=payload.topic_tag,
                    cognitive_level=payload.cognitive_level,
                ),
            )
        except QuestionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except QuestionValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "data": {
            "id": question.id,
            "difficulty": question.difficulty,
            "difficulty_level": question.difficulty_level,
            "discrimination_index": question.discrimination_index,
            "topic_tag": question.topic_tag,
            "cognitive_level": question.cognitive_level,
        },
    }


@router.get("/questions/usage-stats")
def get_question_usage_stats(request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = QuestionService(uow.questions)
        stats = service.get_question_usage_statistics()

    return {"status": "success", "data": stats}


@router.post("/exams/{exam_id}/questions/recalibrate")
def recalibrate_exam_questions(
    exam_id: str,
    payload: QuestionRecalibrationSchema,
    request: Request,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = QuestionCalibrationService(
            uow.analytics,
            uow.questions,
            uow.exams,
            recalibration_repo=uow.recalibration_runs,
            audit_service=AuditService(uow.audit_events),
        )
        try:
            data = service.recalibrate_exam_questions(
                exam_id,
                QuestionRecalibrationRequest(
                    min_attempts=payload.min_attempts,
                    apply=payload.apply,
                    actor_id=x_admin_id,
                ),
            )
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except QuestionCalibrationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/exams/{exam_id}/questions/recalibration-runs")
def list_question_recalibration_runs(
    exam_id: str,
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = QuestionCalibrationService(
            uow.analytics,
            uow.questions,
            uow.exams,
            recalibration_repo=uow.recalibration_runs,
            audit_service=AuditService(uow.audit_events),
        )
        try:
            data = service.list_recalibration_history(exam_id, limit=limit)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except QuestionCalibrationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/exams/{exam_id}/questions/recalibration-runs/{run_id}")
def get_question_recalibration_run(
    exam_id: str,
    run_id: str,
    request: Request,
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = QuestionCalibrationService(
            uow.analytics,
            uow.questions,
            uow.exams,
            recalibration_repo=uow.recalibration_runs,
            audit_service=AuditService(uow.audit_events),
        )
        try:
            data = service.get_recalibration_run(exam_id, run_id)
        except (ExamNotFoundError, RecalibrationRunNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except QuestionCalibrationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/exams/{exam_id}/questions/recalibration-runs/{run_id}/rollback")
def rollback_question_recalibration_run(
    exam_id: str,
    run_id: str,
    request: Request,
    payload: QuestionRecalibrationRollbackSchema | None = None,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = QuestionCalibrationService(
            uow.analytics,
            uow.questions,
            uow.exams,
            recalibration_repo=uow.recalibration_runs,
            audit_service=AuditService(uow.audit_events),
        )
        try:
            data = service.rollback_recalibration_run(
                exam_id,
                run_id,
                QuestionRecalibrationRollbackRequest(
                    actor_id=x_admin_id,
                    reason=None if payload is None else payload.reason,
                ),
            )
        except (ExamNotFoundError, RecalibrationRunNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (QuestionCalibrationError, RecalibrationRollbackError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


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


@router.post("/exams/import-question-pack-csv")
async def import_exam_question_pack_csv(
    request: Request,
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = (await file.read()).decode("utf-8", errors="replace")

    db = request.app.state.db
    with UnitOfWork(db) as uow:
        question_service = QuestionService(uow.questions)
        exam_service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
        import_service = ExamQuestionPackageCsvImportService(
            question_service,
            exam_service,
        )
        try:
            result = import_service.import_csv(content)
        except (
            CsvImportError,
            ExamValidationError,
            ExamAlreadyPublishedError,
            QuestionValidationError,
        ) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "data": {
            "exam_id": result.exam_id,
            "exam_name": result.exam_name,
            "duration_minutes": result.duration_minutes,
            "negative_marking": result.negative_marking,
            "published": result.published,
            "total_rows": result.total_rows,
            "inserted": result.inserted,
            "failed": result.failed,
            "question_ids": result.question_ids,
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


@router.post("/exams/{exam_id}/pause")
def pause_exam_attempts(
    exam_id: str,
    request: Request,
    payload: ExamControlSchema | None = None,
    limit: int = Query(default=2000, ge=1, le=5000),
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = DeliveryService(
            uow.attempts,
            uow.exams,
            uow.questions,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
            analytics_repo=uow.analytics,
        )
        try:
            data = service.pause_exam_attempts(
                exam_id=exam_id,
                actor_id=x_admin_id,
                reason=None if payload is None else payload.reason,
                limit=limit,
            )
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (AttemptStateError, DeliveryError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/exams/{exam_id}/resume")
def resume_exam_attempts(
    exam_id: str,
    request: Request,
    payload: ExamControlSchema | None = None,
    limit: int = Query(default=2000, ge=1, le=5000),
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = DeliveryService(
            uow.attempts,
            uow.exams,
            uow.questions,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
            analytics_repo=uow.analytics,
        )
        try:
            data = service.resume_exam_attempts(
                exam_id=exam_id,
                actor_id=x_admin_id,
                reason=None if payload is None else payload.reason,
                limit=limit,
            )
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (AttemptStateError, DeliveryError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/exams/{exam_id}/broadcast")
def broadcast_to_candidates(
    exam_id: str,
    payload: AdminBroadcastSchema,
    request: Request,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = DeliveryService(
            uow.attempts,
            uow.exams,
            uow.questions,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
            analytics_repo=uow.analytics,
        )
        try:
            data = service.publish_exam_broadcast(
                exam_id=exam_id,
                message=payload.message,
                severity=payload.severity,
                actor_id=x_admin_id,
            )
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DeliveryError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


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


@router.get("/exams/{exam_id}/analytics/difficulty-heatmap")
def get_difficulty_heatmap(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = AnalyticsService(uow.analytics, uow.exams)
        try:
            data = service.get_question_difficulty_heatmap(exam_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/exams/{exam_id}/analytics/topic-heatmap")
def get_topic_heatmap(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = AnalyticsService(uow.analytics, uow.exams)
        try:
            data = service.get_topic_performance_heatmap(exam_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/exams/{exam_id}/analytics/score-distribution")
def get_score_distribution(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = AnalyticsService(uow.analytics, uow.exams)
        try:
            data = service.get_score_distribution(exam_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/attempts/{attempt_id}/timeline")
def get_attempt_timeline(attempt_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = AuditService(uow.audit_events)
        timeline = service.list_entity_timeline(entity_type="attempt", entity_id=attempt_id)

    return {"status": "success", "data": timeline}


@router.get("/audit/events")
def search_audit_events(
    request: Request,
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    actor_type: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = AuditService(uow.audit_events)
        try:
            events = service.search_events(
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                since=since,
                until=until,
                limit=limit,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "data": {
            "count": len(events),
            "events": events,
        },
    }


@router.post("/attempts/{attempt_id}/force-submit")
def force_submit_attempt(
    attempt_id: str,
    request: Request,
    payload: ForceSubmitSchema | None = None,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = DeliveryService(
            uow.attempts,
            uow.exams,
            uow.questions,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
            analytics_repo=uow.analytics,
        )
        try:
            data = service.force_finalize_attempt_by_admin(
                attempt_id=attempt_id,
                actor_id=x_admin_id,
                reason=None if payload is None else payload.reason,
            )
        except AttemptStateError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except DeliveryError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/attempts/force-submit-expired")
def force_submit_expired_attempts(
    request: Request,
    exam_id: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = DeliveryService(
            uow.attempts,
            uow.exams,
            uow.questions,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
            analytics_repo=uow.analytics,
        )
        try:
            data = service.force_finalize_expired_attempts(
                actor_id=x_admin_id,
                exam_id=exam_id,
                limit=limit,
            )
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DeliveryError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/system/metrics")
def get_system_metrics(request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        data = MetricsService(uow.metrics).get_metrics()

    return {"status": "success", "data": data}


@router.get("/students")
def list_student_accounts(
    request: Request,
    limit: int = Query(default=300, ge=1, le=1000),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = StudentRegistryService(uow.student_accounts)
        students = service.list_students(limit=limit)

    return {
        "status": "success",
        "data": {
            "count": len(students),
            "students": students,
        },
    }


@router.post("/students/register", status_code=status.HTTP_201_CREATED)
def register_student_account(
    payload: StudentRegisterSchema,
    request: Request,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = StudentRegistryService(uow.student_accounts)
        try:
            student = service.register_student(
                StudentRegisterPayload(
                    student_id=payload.student_id,
                    display_name=payload.display_name,
                    created_by=x_admin_id,
                )
            )
        except StudentAlreadyExistsError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except StudentValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": student}


@router.post("/students/generate")
def generate_student_accounts(
    payload: StudentGenerateSchema,
    request: Request,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = StudentRegistryService(uow.student_accounts)
        try:
            data = service.generate_students(
                StudentGeneratePayload(
                    prefix=payload.prefix,
                    count=payload.count,
                    created_by=x_admin_id,
                )
            )
        except StudentValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/students/import-csv")
async def import_student_accounts_csv(
    request: Request,
    file: UploadFile = File(...),
    x_admin_id: str = Header(default="admin"),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = (await file.read()).decode("utf-8", errors="replace")

    db = request.app.state.db
    with UnitOfWork(db) as uow:
        registry_service = StudentRegistryService(uow.student_accounts)
        csv_service = StudentRegistryCsvService(registry_service)
        try:
            result = csv_service.import_csv(content, default_created_by=x_admin_id)
        except StudentCsvError as exc:
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


@router.get("/students/export-csv")
def export_student_accounts_csv(
    request: Request,
    limit: int = Query(default=1000, ge=1, le=5000),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        registry_service = StudentRegistryService(uow.student_accounts)
        csv_service = StudentRegistryCsvService(registry_service)
        content = csv_service.export_csv(limit=limit)

    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="student_accounts.csv"',
        },
    )


@router.get("/students/{student_id}/performance")
def get_student_performance(student_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = AnalyticsService(uow.analytics, uow.exams)
        performance = service.get_student_performance(student_id)

    return {"status": "success", "data": performance}


@router.get("/exams/{exam_id}/active-attempts")
def get_active_attempts(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = ProctoringService(uow.attempts, uow.exams)
        try:
            data = service.get_active_attempts(exam_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/exams/{exam_id}/live-status")
def get_exam_live_status(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = ProctoringService(uow.attempts, uow.exams)
        try:
            data = service.get_live_status(exam_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/proctor/dashboard")
def get_proctor_dashboard(
    request: Request,
    active_limit: int = Query(default=200, ge=1, le=1000),
    finalize_limit: int = Query(default=50, ge=1, le=500),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = ProctoringService(uow.attempts, uow.exams)
        try:
            data = service.get_dashboard(
                active_limit=active_limit,
                finalize_limit=finalize_limit,
            )
        except ProctoringValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/proctor/alerts/sync")
def sync_proctor_alerts(
    request: Request,
    exam_id: str | None = Query(default=None),
    active_limit: int = Query(default=500, ge=1, le=1000),
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        proctoring = ProctoringService(uow.attempts, uow.exams)
        service = ProctorAlertService(
            alert_repo=uow.proctor_alerts,
            exam_repo=uow.exams,
            proctoring_service=proctoring,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
        )
        try:
            data = service.sync_alerts(
                exam_id=exam_id,
                active_limit=active_limit,
                triggered_by=x_admin_id,
            )
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ProctorAlertValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/proctor/alerts")
def list_proctor_alerts(
    request: Request,
    exam_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=200, ge=1, le=1000),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        proctoring = ProctoringService(uow.attempts, uow.exams)
        service = ProctorAlertService(
            alert_repo=uow.proctor_alerts,
            exam_repo=uow.exams,
            proctoring_service=proctoring,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
        )
        try:
            data = service.list_alerts(
                exam_id=exam_id,
                status=status_filter,
                limit=limit,
            )
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ProctorAlertValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/proctor/alerts/summary")
def get_proctor_alert_summary(
    request: Request,
    exam_id: str | None = Query(default=None),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        proctoring = ProctoringService(uow.attempts, uow.exams)
        service = ProctorAlertService(
            alert_repo=uow.proctor_alerts,
            exam_repo=uow.exams,
            proctoring_service=proctoring,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
        )
        try:
            data = service.get_alert_summary(exam_id=exam_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ProctorAlertValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/proctor/alerts/metrics")
def get_proctor_alert_metrics(
    request: Request,
    exam_id: str | None = Query(default=None),
    stale_after_minutes: int = Query(default=15, ge=1, le=10080),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        proctoring = ProctoringService(uow.attempts, uow.exams)
        service = ProctorAlertService(
            alert_repo=uow.proctor_alerts,
            exam_repo=uow.exams,
            proctoring_service=proctoring,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
        )
        try:
            data = service.get_operational_metrics(
                exam_id=exam_id,
                stale_after_minutes=stale_after_minutes,
            )
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ProctorAlertValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/exams/{exam_id}/proctor-alerts/live")
def get_exam_live_proctor_alerts(
    exam_id: str,
    request: Request,
    limit: int = Query(default=200, ge=1, le=1000),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        proctoring = ProctoringService(uow.attempts, uow.exams)
        service = ProctorAlertService(
            alert_repo=uow.proctor_alerts,
            exam_repo=uow.exams,
            proctoring_service=proctoring,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
        )
        try:
            data = service.get_live_alerts(exam_id=exam_id, limit=limit)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ProctorAlertValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/proctor/alerts/{alert_id}/acknowledge")
def acknowledge_proctor_alert(
    alert_id: str,
    request: Request,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        proctoring = ProctoringService(uow.attempts, uow.exams)
        service = ProctorAlertService(
            alert_repo=uow.proctor_alerts,
            exam_repo=uow.exams,
            proctoring_service=proctoring,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
        )
        try:
            data = service.acknowledge_alert(alert_id=alert_id, actor_id=x_admin_id)
        except ProctorAlertNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ProctorAlertValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/proctor/alerts/{alert_id}/resolve")
def resolve_proctor_alert(
    alert_id: str,
    request: Request,
    payload: ProctorAlertResolveSchema | None = None,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        proctoring = ProctoringService(uow.attempts, uow.exams)
        service = ProctorAlertService(
            alert_repo=uow.proctor_alerts,
            exam_repo=uow.exams,
            proctoring_service=proctoring,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
        )
        try:
            data = service.resolve_alert(
                alert_id=alert_id,
                actor_id=x_admin_id,
                note=None if payload is None else payload.note,
            )
        except ProctorAlertNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ProctorAlertValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/proctor/events")
def get_proctor_event_stream(
    request: Request,
    exam_id: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
    since: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = ProctoringService(uow.attempts, uow.exams)
        try:
            data = service.get_event_stream(
                limit=limit,
                cursor=cursor,
                since=since,
                exam_id=exam_id,
            )
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ProctoringValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}
