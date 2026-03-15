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
    AdminAccountCreateSchema,
    AdminBroadcastSchema,
    AIFibClusterSchema,
    AIQuestionRefineSchema,
    AIRubricSuggestSchema,
    AISubjectiveSuggestSchema,
    DownloadAssetCreateSchema,
    DownloadAssetUpdateSchema,
    ExamCreateSchema,
    ExamControlSchema,
    ExamReferenceUpdateSchema,
    ExamRulesUpdateSchema,
    FibReviewDecisionSchema,
    ForceSubmitSchema,
    ProctorAlertResolveSchema,
    QuestionCreateSchema,
    QuestionMetadataUpdateSchema,
    QuestionRecalibrationSchema,
    QuestionRecalibrationRollbackSchema,
    StudentGenerateSchema,
    StudentRegisterSchema,
    SubjectiveReviewSchema,
)
from phase1_server.services.download_asset_service import (
    DownloadAssetConflictError,
    DownloadAssetNotFoundError,
    DownloadAssetService,
    DownloadAssetValidationError,
)
from phase1_server.services.analytics_service import AnalyticsService
from phase1_server.services.admin_account_service import (
    AdminAccountCreatePayload,
    AdminAccountService,
    AdminAuthorizationError,
    AdminValidationError,
)
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import (
    AttemptStateError,
    DeliveryError,
    DeliveryService,
)
from phase1_server.services.exam_service import (
    ExamAlreadyPublishedError,
    ExamDeleteBlockedError,
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
from phase1_server.services.local_ai_service import LocalAISidecarService
from phase1_server.services.proctoring_service import (
    ProctoringService,
    ProctoringValidationError,
)
from phase1_server.services.grading_service import ResultNotReadyError
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
from phase1_server.services.review_service import (
    ReviewError,
    ReviewNotFoundError,
    ReviewService,
    ReviewValidationError,
)
from phase1_server.services.result_export_service import (
    ResultArtifactNotReadyError,
    ResultExportError,
    ResultExportService,
    ResultPublicationError,
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
from phase1_server.models import AdminIdentity, AdminRole

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_only)])


def _admin_identity(request: Request) -> AdminIdentity:
    identity = getattr(request.state, "admin_identity", None)
    if isinstance(identity, AdminIdentity):
        return identity
    return AdminIdentity(admin_id="admin", role=AdminRole.SUPERADMIN)


def _ensure_exam_access(uow: UnitOfWork, request: Request, exam_id: str):
    exam = uow.exams.get_exam(exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail=f"Exam '{exam_id}' not found")
    admin = _admin_identity(request)
    if not admin.is_superadmin and exam.owner_admin_id != admin.admin_id:
        raise HTTPException(status_code=403, detail="Exam access is restricted to the owning examiner")
    return admin, exam


def _ensure_question_access(uow: UnitOfWork, request: Request, question_id: str):
    question = uow.questions.get_question(question_id)
    if question is None:
        raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found")
    admin = _admin_identity(request)
    if not admin.is_superadmin and question.owner_admin_id != admin.admin_id:
        raise HTTPException(status_code=403, detail="Question access is restricted to the owning examiner")
    return admin, question


def _ensure_attempt_access(uow: UnitOfWork, request: Request, attempt_id: str):
    attempt = uow.attempts.get(attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail=f"Attempt '{attempt_id}' not found")
    admin, _ = _ensure_exam_access(uow, request, attempt.exam_id)
    return admin, attempt


def _result_service(uow: UnitOfWork) -> ResultExportService:
    return ResultExportService(
        uow.attempts,
        uow.exams,
        uow.questions,
        uow.student_accounts,
        uow.result_artifacts,
        audit_service=AuditService(uow.audit_events),
        analytics_service=AnalyticsService(uow.analytics, uow.exams),
    )


@router.post("/questions", status_code=status.HTTP_201_CREATED)
def create_question(payload: QuestionCreateSchema, request: Request):
    db = request.app.state.db
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        service = QuestionService(uow.questions)
        try:
            question = service.create_question(
                QuestionCreatePayload(
                    text=payload.text,
                    topic=payload.topic,
                    difficulty=payload.difficulty,
                    marks=payload.marks,
                    owner_admin_id=admin.admin_id,
                    created_by=admin.admin_id,
                    question_type=payload.question_type,
                    difficulty_level=payload.difficulty_level,
                    discrimination_index=payload.discrimination_index,
                    topic_tag=payload.topic_tag,
                    cognitive_level=payload.cognitive_level,
                    options=[
                        (option.option_text, option.is_correct)
                        for option in (payload.options or [])
                    ]
                    or None,
                    accepted_answers=payload.accepted_answers,
                    word_target_min=payload.word_target_min,
                    word_target_max=payload.word_target_max,
                    word_hard_max=payload.word_hard_max,
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
            "question_type": question.question_type.value,
            "difficulty_level": question.difficulty_level,
            "discrimination_index": question.discrimination_index,
            "topic_tag": question.topic_tag,
            "cognitive_level": question.cognitive_level,
            "word_target_min": question.word_target_min,
            "word_target_max": question.word_target_max,
            "word_hard_max": question.word_hard_max,
        },
    }


@router.get("/questions")
def list_questions(request: Request):
    db = request.app.state.db
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        service = QuestionService(uow.questions)
        items = service.list_questions(
            owner_admin_id=admin.admin_id,
            include_all=admin.is_superadmin,
        )

    return {"status": "success", "data": items}


@router.delete("/questions/{question_id}")
def delete_question(question_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        _ensure_question_access(uow, request, question_id)
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
        _ensure_question_access(uow, request, question_id)
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
                    word_target_min=payload.word_target_min,
                    word_target_max=payload.word_target_max,
                    word_hard_max=payload.word_hard_max,
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
            "word_target_min": question.word_target_min,
            "word_target_max": question.word_target_max,
            "word_hard_max": question.word_hard_max,
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
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        question_service = QuestionService(uow.questions)
        import_service = QuestionCsvImportService(question_service)
        try:
            result = import_service.import_csv(
                content,
                owner_admin_id=admin.admin_id,
                created_by=admin.admin_id,
            )
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
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        question_service = QuestionService(uow.questions)
        exam_service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
        import_service = ExamQuestionPackageCsvImportService(
            question_service,
            exam_service,
        )
        try:
            result = import_service.import_csv(
                content,
                owner_admin_id=admin.admin_id,
                created_by=admin.admin_id,
            )
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
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
        try:
            exam = service.create_exam(
                ExamCreatePayload(
                    name=payload.name,
                    duration_minutes=payload.duration_minutes,
                    negative_marking=payload.negative_marking,
                    owner_admin_id=admin.admin_id,
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
            "owner_admin_id": exam.owner_admin_id,
            "reference_exam_id": exam.reference_exam_id,
            "custom_rules": exam.custom_rules or [],
            "results_published": exam.results_published,
            "results_published_at": exam.results_published_at,
            "results_published_by": exam.results_published_by,
        },
    }


@router.post("/exams/{exam_id}/add-questions")
def add_questions(exam_id: str, payload: AddQuestionsSchema, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        admin, _ = _ensure_exam_access(uow, request, exam_id)
        if not admin.is_superadmin:
            for question_id in payload.question_ids:
                question = uow.questions.get_question(question_id)
                if question is None:
                    raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found")
                if question.owner_admin_id != admin.admin_id:
                    raise HTTPException(
                        status_code=403,
                        detail="Examiners can attach only their own questions",
                    )
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


@router.patch("/exams/{exam_id}/reference-exam")
def set_reference_exam(
    exam_id: str,
    payload: ExamReferenceUpdateSchema,
    request: Request,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        admin, _ = _ensure_exam_access(uow, request, exam_id)
        service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
        try:
            exam = service.set_reference_exam(
                exam_id=exam_id,
                reference_exam_id=payload.reference_exam_id,
                actor_id=admin.admin_id,
                actor_role=admin.role.value,
            )
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ExamValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "data": {
            "id": exam.id,
            "reference_exam_id": exam.reference_exam_id,
        },
    }


@router.patch("/exams/{exam_id}/rules")
def update_exam_rules(
    exam_id: str,
    payload: ExamRulesUpdateSchema,
    request: Request,
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        admin, _ = _ensure_exam_access(uow, request, exam_id)
        service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
        try:
            exam = service.set_custom_rules(
                exam_id=exam_id,
                custom_rules=payload.custom_rules,
                actor_id=admin.admin_id,
                actor_role=admin.role.value,
            )
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ExamValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "status": "success",
        "data": {
            "id": exam.id,
            "custom_rules": exam.custom_rules or [],
        },
    }


@router.post("/exams/{exam_id}/publish")
def publish_exam(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        _ensure_exam_access(uow, request, exam_id)
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
        admin, _ = _ensure_exam_access(uow, request, exam_id)
        service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
        try:
            exam = service.close_exam(exam_id, actor_id=admin.admin_id, actor_role=admin.role.value)
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
        admin, _ = _ensure_exam_access(uow, request, exam_id)
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
                actor_id=admin.admin_id,
                reason=None if payload is None else payload.reason,
                freeze_timer=False if payload is None else payload.freeze_timer,
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
        admin, _ = _ensure_exam_access(uow, request, exam_id)
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
                actor_id=admin.admin_id,
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
        admin, _ = _ensure_exam_access(uow, request, exam_id)
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
                actor_id=admin.admin_id,
            )
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DeliveryError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/exams")
def list_exams(request: Request):
    db = request.app.state.db
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
        exams = service.list_exams(owner_admin_id=admin.admin_id, include_all=admin.is_superadmin)

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
                "owner_admin_id": exam.owner_admin_id,
                "reference_exam_id": exam.reference_exam_id,
                "custom_rules": exam.custom_rules or [],
                "results_published": exam.results_published,
                "results_published_at": exam.results_published_at,
                "results_published_by": exam.results_published_by,
            }
            for exam in exams
        ],
    }


@router.get("/accounts")
def list_admin_accounts(request: Request):
    db = request.app.state.db
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        service = AdminAccountService(uow.admin_accounts)
        try:
            accounts = service.list_accounts(admin)
        except AdminAuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"status": "success", "data": accounts}


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_admin_account(payload: AdminAccountCreateSchema, request: Request):
    db = request.app.state.db
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        service = AdminAccountService(uow.admin_accounts)
        try:
            account = service.create_account(
                AdminAccountCreatePayload(
                    admin_id=payload.admin_id,
                    display_name=payload.display_name,
                    role=payload.role,
                    access_key=payload.access_key,
                    created_by=admin.admin_id,
                ),
                viewer=admin,
            )
        except AdminAuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except AdminValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "data": account}


@router.get("/exams/{exam_id}/fib-review-queue")
def list_fib_review_queue(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        _ensure_exam_access(uow, request, exam_id)
        service = ReviewService(
            uow.attempts,
            uow.exams,
            uow.questions,
            audit_service=AuditService(uow.audit_events),
        )
        try:
            data = service.list_fib_review_queue(exam_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ReviewError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "data": data}


@router.post("/exams/{exam_id}/fib-review-decisions")
def apply_fib_review_decision(
    exam_id: str,
    payload: FibReviewDecisionSchema,
    request: Request,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        admin, _ = _ensure_exam_access(uow, request, exam_id)
        service = ReviewService(
            uow.attempts,
            uow.exams,
            uow.questions,
            audit_service=AuditService(uow.audit_events),
        )
        try:
            data = service.apply_fib_decision(
                exam_id=exam_id,
                question_id=payload.question_id,
                normalized_text_answer=payload.normalized_text_answer,
                decision=payload.decision,
                canonical_answer_text=payload.canonical_answer_text,
                reviewer_id=admin.admin_id,
            )
        except (ExamNotFoundError, ReviewNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ReviewValidationError, ReviewError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "data": data}


@router.get("/exams/{exam_id}/subjective-review-queue")
def list_subjective_review_queue(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        _ensure_exam_access(uow, request, exam_id)
        service = ReviewService(
            uow.attempts,
            uow.exams,
            uow.questions,
            audit_service=AuditService(uow.audit_events),
        )
        try:
            data = service.list_subjective_review_queue(exam_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ReviewError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "data": data}


@router.post("/attempts/{attempt_id}/subjective-review")
def score_subjective_answer(
    attempt_id: str,
    payload: SubjectiveReviewSchema,
    request: Request,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        admin, _ = _ensure_attempt_access(uow, request, attempt_id)
        service = ReviewService(
            uow.attempts,
            uow.exams,
            uow.questions,
            audit_service=AuditService(uow.audit_events),
        )
        try:
            data = service.score_subjective_answer(
                attempt_id=attempt_id,
                question_id=payload.question_id,
                marks_awarded=payload.marks_awarded,
                reviewer_id=admin.admin_id,
                review_note=payload.review_note,
            )
        except ReviewNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ReviewValidationError, ReviewError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "data": data}


@router.delete("/exams/{exam_id}")
def delete_exam(
    exam_id: str,
    request: Request,
    x_admin_id: str = Header(default="admin"),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        admin, _ = _ensure_exam_access(uow, request, exam_id)
        service = ExamService(uow.exams, uow.questions, AuditService(uow.audit_events))
        try:
            data = service.delete_exam(exam_id, actor_id=admin.admin_id, actor_role=admin.role.value)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ExamDeleteBlockedError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/exams/{exam_id}/analytics")
def get_exam_analytics(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        _ensure_exam_access(uow, request, exam_id)
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
        _ensure_exam_access(uow, request, exam_id)
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
        _ensure_exam_access(uow, request, exam_id)
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
        _ensure_exam_access(uow, request, exam_id)
        service = AnalyticsService(uow.analytics, uow.exams)
        try:
            data = service.get_score_distribution(exam_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/ai/status")
def get_local_ai_status(request: Request):
    service = LocalAISidecarService(request.app.state.settings)
    return {"status": "success", "data": service.status()}


@router.post("/ai/question-refine")
def refine_question_with_ai(payload: AIQuestionRefineSchema, request: Request):
    admin = _admin_identity(request)
    service = LocalAISidecarService(request.app.state.settings)
    data = service.refine_question(
        question_text=payload.question_text,
        question_type=payload.question_type,
        topic=payload.topic,
        marks=float(payload.marks),
    )
    with UnitOfWork(request.app.state.db) as uow:
        AuditService(uow.audit_events).log_event(
            entity_type="ai",
            entity_id="question_refine",
            actor_type="admin",
            actor_id=admin.admin_id,
            event_type="AI_QUESTION_REFINED",
            payload={"provider": data.get("provider", "heuristic")},
        )
    return {"status": "success", "data": data}


@router.post("/ai/rubric-suggest")
def suggest_rubric_with_ai(payload: AIRubricSuggestSchema, request: Request):
    admin = _admin_identity(request)
    service = LocalAISidecarService(request.app.state.settings)
    data = service.suggest_rubric(
        question_text=payload.question_text,
        question_type=payload.question_type,
        max_marks=float(payload.max_marks),
    )
    with UnitOfWork(request.app.state.db) as uow:
        AuditService(uow.audit_events).log_event(
            entity_type="ai",
            entity_id="rubric_suggest",
            actor_type="admin",
            actor_id=admin.admin_id,
            event_type="AI_RUBRIC_SUGGESTED",
            payload={"provider": data.get("provider", "heuristic")},
        )
    return {"status": "success", "data": data}


@router.post("/ai/fib-cluster")
def cluster_fib_with_ai(payload: AIFibClusterSchema, request: Request):
    admin = _admin_identity(request)
    service = LocalAISidecarService(request.app.state.settings)
    data = service.cluster_fib_answers(
        question_text=payload.question_text,
        answers=payload.answers,
    )
    with UnitOfWork(request.app.state.db) as uow:
        AuditService(uow.audit_events).log_event(
            entity_type="ai",
            entity_id="fib_cluster",
            actor_type="admin",
            actor_id=admin.admin_id,
            event_type="AI_FIB_CLUSTERED",
            payload={"provider": data.get("provider", "heuristic"), "answer_count": len(payload.answers)},
        )
    return {"status": "success", "data": data}


@router.post("/ai/subjective-suggest")
def suggest_subjective_with_ai(payload: AISubjectiveSuggestSchema, request: Request):
    admin = _admin_identity(request)
    service = LocalAISidecarService(request.app.state.settings)
    data = service.suggest_subjective_score(
        question_text=payload.question_text,
        question_type=payload.question_type,
        answer_text=payload.answer_text,
        max_marks=float(payload.max_marks),
    )
    with UnitOfWork(request.app.state.db) as uow:
        AuditService(uow.audit_events).log_event(
            entity_type="ai",
            entity_id="subjective_suggest",
            actor_type="admin",
            actor_id=admin.admin_id,
            event_type="AI_SUBJECTIVE_SUGGESTED",
            payload={"provider": data.get("provider", "heuristic")},
        )
    return {"status": "success", "data": data}


@router.post("/exams/{exam_id}/ai/analytics-summary")
def summarize_exam_analytics_with_ai(exam_id: str, request: Request):
    db = request.app.state.db
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        _ensure_exam_access(uow, request, exam_id)
        analytics = AnalyticsService(uow.analytics, uow.exams).get_exam_analytics(exam_id)
        exam = uow.exams.get_exam(exam_id)
        if exam is None:
            raise HTTPException(status_code=404, detail=f"Exam '{exam_id}' not found")
        data = LocalAISidecarService(request.app.state.settings).summarize_exam_analytics(
            exam_name=exam.name,
            analytics_payload=analytics,
        )
        AuditService(uow.audit_events).log_event(
            entity_type="exam",
            entity_id=exam_id,
            actor_type="admin",
            actor_id=admin.admin_id,
            event_type="AI_ANALYTICS_SUMMARY_GENERATED",
            payload={"provider": data.get("provider", "heuristic")},
        )
    return {"status": "success", "data": data}


@router.get("/exams/{exam_id}/results")
def list_exam_results(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        _ensure_exam_access(uow, request, exam_id)
        data = _result_service(uow).list_exam_results(exam_id)
    return {"status": "success", "data": data}


@router.post("/exams/{exam_id}/results/publish")
def publish_exam_results(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        admin, _ = _ensure_exam_access(uow, request, exam_id)
        try:
            data = _result_service(uow).publish_exam_results(exam_id, admin.admin_id, admin.role.value)
        except (ExamNotFoundError, ResultPublicationError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "data": data}


@router.post("/exams/{exam_id}/results/unpublish")
def unpublish_exam_results(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        admin, _ = _ensure_exam_access(uow, request, exam_id)
        try:
            data = _result_service(uow).unpublish_exam_results(exam_id, admin.admin_id, admin.role.value)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "success", "data": data}


@router.get("/exams/{exam_id}/results/export.csv")
def export_exam_results_csv(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        admin, _ = _ensure_exam_access(uow, request, exam_id)
        try:
            content = _result_service(uow).export_exam_results_csv(exam_id, admin.admin_id)
        except (ExamNotFoundError, ResultArtifactNotReadyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="exam_results_{exam_id}.csv"'},
    )


@router.get("/exams/{exam_id}/results/pending-review.csv")
def export_pending_review_csv(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        admin, _ = _ensure_exam_access(uow, request, exam_id)
        try:
            content = _result_service(uow).export_pending_review_csv(exam_id, admin.admin_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="pending_review_{exam_id}.csv"'},
    )


@router.get("/attempts/{attempt_id}/result-preview")
def preview_candidate_result(attempt_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        admin, _ = _ensure_attempt_access(uow, request, attempt_id)
        try:
            html = _result_service(uow).render_result_preview_html(attempt_id, admin.admin_id)
        except (ResultExportError, ResultNotReadyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/attempts/{attempt_id}/result-sheet.pdf")
def download_candidate_result_pdf(attempt_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        admin, _ = _ensure_attempt_access(uow, request, attempt_id)
        try:
            pdf = _result_service(uow).export_result_pdf(attempt_id, admin.admin_id)
        except (ResultExportError, ResultArtifactNotReadyError, ResultNotReadyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="result_sheet_{attempt_id}.pdf"'},
    )


@router.get("/artifacts")
def list_result_artifacts(
    request: Request,
    exam_id: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=200),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        if exam_id:
            _ensure_exam_access(uow, request, exam_id)
        data = _result_service(uow).list_artifacts(exam_id=exam_id, limit=limit)
    return {"status": "success", "data": data}


@router.get("/download-assets")
def list_download_assets(request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = DownloadAssetService(audit_service=AuditService(uow.audit_events))
        data = service.list_assets()
    return {"status": "success", "data": data}


@router.get("/download-assets/{asset_path:path}")
def get_download_asset(asset_path: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        service = DownloadAssetService(audit_service=AuditService(uow.audit_events))
        try:
            data = service.get_asset(asset_path)
        except DownloadAssetNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DownloadAssetValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "data": data}


@router.put("/download-assets/{asset_path:path}")
def update_download_asset(asset_path: str, payload: DownloadAssetUpdateSchema, request: Request):
    db = request.app.state.db
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        service = DownloadAssetService(audit_service=AuditService(uow.audit_events))
        try:
            data = service.update_asset(asset_path, payload.content, admin.admin_id)
        except DownloadAssetNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except DownloadAssetValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "data": data}


@router.post("/download-assets", status_code=status.HTTP_201_CREATED)
def create_download_asset(payload: DownloadAssetCreateSchema, request: Request):
    db = request.app.state.db
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        service = DownloadAssetService(audit_service=AuditService(uow.audit_events))
        try:
            data = service.create_asset(payload.file_name, payload.content, admin.admin_id)
        except DownloadAssetConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except DownloadAssetValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "success", "data": data}


@router.get("/attempts/{attempt_id}/timeline")
def get_attempt_timeline(attempt_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        _ensure_attempt_access(uow, request, attempt_id)
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
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        if entity_type == "exam" and entity_id:
            _ensure_exam_access(uow, request, entity_id)
        service = AuditService(uow.audit_events)
        try:
            events = service.search_events(
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id if admin.is_superadmin else (actor_id or admin.admin_id),
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
        admin, _ = _ensure_attempt_access(uow, request, attempt_id)
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
                actor_id=admin.admin_id,
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
        admin = _admin_identity(request)
        if exam_id:
            _ensure_exam_access(uow, request, exam_id)
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
                actor_id=admin.admin_id,
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
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        service = StudentRegistryService(uow.student_accounts)
        students = service.list_students(
            limit=limit,
            owner_admin_id=admin.admin_id,
            include_all=admin.is_superadmin,
        )

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
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        service = StudentRegistryService(uow.student_accounts)
        try:
            student = service.register_student(
                StudentRegisterPayload(
                    student_id=payload.student_id,
                    display_name=payload.display_name,
                    created_by=admin.admin_id,
                    password=payload.password,
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
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        service = StudentRegistryService(uow.student_accounts)
        try:
            data = service.generate_students(
                StudentGeneratePayload(
                    prefix=payload.prefix,
                    count=payload.count,
                    created_by=admin.admin_id,
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
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        registry_service = StudentRegistryService(uow.student_accounts)
        csv_service = StudentRegistryCsvService(registry_service)
        try:
            result = csv_service.import_csv(content, default_created_by=admin.admin_id)
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
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        registry_service = StudentRegistryService(uow.student_accounts)
        csv_service = StudentRegistryCsvService(registry_service)
        content = csv_service.export_csv(
            limit=limit if admin.is_superadmin else min(limit, 1000),
            owner_admin_id=admin.admin_id,
            include_all=admin.is_superadmin,
        )

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
    admin = _admin_identity(request)
    with UnitOfWork(db) as uow:
        if not admin.is_superadmin:
            record = uow.student_accounts.get_student_auth_record(student_id)
            if record is None or record.get("owner_admin_id") != admin.admin_id:
                raise HTTPException(status_code=403, detail="Student performance access is restricted")
        service = AnalyticsService(uow.analytics, uow.exams)
        performance = service.get_student_performance(student_id)

    return {"status": "success", "data": performance}


@router.get("/exams/{exam_id}/active-attempts")
def get_active_attempts(exam_id: str, request: Request):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        _ensure_exam_access(uow, request, exam_id)
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
        _ensure_exam_access(uow, request, exam_id)
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
