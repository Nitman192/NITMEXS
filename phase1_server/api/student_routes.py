"""Student routes for exam delivery flow."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from phase1_server.api.deps import student_identity
from phase1_server.schemas import (
    AIExplainRequestSchema,
    AnswerSubmitSchema,
    BroadcastReceiptSchema,
    StudentIssueReportSchema,
    TechnicalIssueReportSchema,
)
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import (
    AnswerSubmissionPayload,
    AnalysisQuestionNotFoundError,
    AttemptStateError,
    DeliveryError,
    DeliveryService,
    OwnershipError,
    SnapshotQuestionNotFoundError,
)
from phase1_server.services.metrics_service import MetricsService
from phase1_server.services.grading_service import (
    GradingError,
    GradingNotFoundError,
    GradingOwnershipError,
    ResultNotReadyError,
)
from phase1_server.services.student_morale_service import StudentMoraleService
from phase1_server.services.exam_service import (
    ExamNotFoundError,
    ExamService,
    ExamValidationError,
)
from phase1_server.uow import UnitOfWork

router = APIRouter(prefix="/student", tags=["student"])


@router.get("/exams")
def list_available_exams(
    request: Request,
    student_id: str = Depends(student_identity),
):
    _ = student_id
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        exams = ExamService(uow.exams, uow.questions).list_exams()

    active = [
        {
            "id": exam.id,
            "name": exam.name,
            "duration_minutes": exam.duration_minutes,
            "status": exam.status.value,
            "published": exam.published,
            "created_at": exam.created_at,
        }
        for exam in exams
        if exam.published or exam.status.value == "ACTIVE"
    ]
    return {"status": "success", "data": active}


@router.post("/exams/{exam_id}/start")
def start_attempt(
    exam_id: str,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.start_attempt(exam_id=exam_id, student_id=student_id)
        except ExamNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ExamValidationError, AttemptStateError, DeliveryError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/attempts/{attempt_id}/questions/{sequence_number}")
def fetch_question(
    attempt_id: str,
    sequence_number: int,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.fetch_question(
                attempt_id=attempt_id,
                sequence_number=sequence_number,
                student_id=student_id,
            )
        except OwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except SnapshotQuestionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (AttemptStateError, DeliveryError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/attempts/{attempt_id}/rules")
def get_attempt_rules(
    attempt_id: str,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.get_attempt_exam_rules(attempt_id=attempt_id, student_id=student_id)
        except OwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (DeliveryError, ExamNotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/attempts/{attempt_id}/status")
def get_attempt_status(
    attempt_id: str,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.get_attempt_status(attempt_id=attempt_id, student_id=student_id)
        except OwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except DeliveryError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/attempts/{attempt_id}/morale")
def get_attempt_morale(
    attempt_id: str,
    request: Request,
    student_id: str = Depends(student_identity),
):
    db = request.app.state.db
    with UnitOfWork(db) as uow:
        delivery = DeliveryService(
            uow.attempts,
            uow.exams,
            uow.questions,
            audit_service=AuditService(uow.audit_events),
            metrics_service=MetricsService(uow.metrics),
            analytics_repo=uow.analytics,
        )
        morale_service = StudentMoraleService()
        try:
            status_data = delivery.get_attempt_status(attempt_id=attempt_id, student_id=student_id)
        except OwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except DeliveryError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        morale = morale_service.build_message(status_data)

    return {"status": "success", "data": {"attempt_id": attempt_id, **morale}}


@router.post("/attempts/{attempt_id}/answers")
def submit_answer(
    attempt_id: str,
    payload: AnswerSubmitSchema,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.submit_answer(
                AnswerSubmissionPayload(
                    attempt_id=attempt_id,
                    question_id=payload.question_id,
                    selected_option_id=payload.selected_option_id,
                    confidence_tag=payload.confidence_tag,
                ),
                student_id=student_id,
            )
        except OwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except SnapshotQuestionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (AttemptStateError, DeliveryError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/attempts/{attempt_id}/question-issue")
def report_question_issue(
    attempt_id: str,
    payload: StudentIssueReportSchema,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.report_question_issue(
                attempt_id=attempt_id,
                question_id=payload.question_id,
                issue_type=payload.issue_type,
                note=payload.note,
                student_id=student_id,
            )
        except OwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except SnapshotQuestionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (AttemptStateError, DeliveryError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/attempts/{attempt_id}/technical-issue")
def report_technical_issue(
    attempt_id: str,
    payload: TechnicalIssueReportSchema,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.report_technical_issue(
                attempt_id=attempt_id,
                issue_type=payload.issue_type,
                note=payload.note,
                student_id=student_id,
            )
        except OwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (AttemptStateError, DeliveryError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/attempts/{attempt_id}/broadcasts")
def list_attempt_broadcasts(
    attempt_id: str,
    request: Request,
    since: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    student_id: str = Depends(student_identity),
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
            data = service.list_attempt_broadcasts(
                attempt_id=attempt_id,
                student_id=student_id,
                since=since,
                limit=limit,
            )
        except OwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except DeliveryError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/attempts/{attempt_id}/broadcasts/ack")
def acknowledge_attempt_broadcasts(
    attempt_id: str,
    payload: BroadcastReceiptSchema,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.acknowledge_attempt_broadcasts(
                attempt_id=attempt_id,
                student_id=student_id,
                broadcast_ids=payload.broadcast_ids,
                received_at=payload.received_at,
            )
        except OwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except DeliveryError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/attempts/{attempt_id}/finalize")
def finalize_attempt(
    attempt_id: str,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.finalize_attempt(attempt_id=attempt_id, student_id=student_id)
        except OwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (AttemptStateError, DeliveryError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/attempts/{attempt_id}/auto-submit")
def auto_submit_attempt(
    attempt_id: str,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.auto_submit_expired_attempt_for_student(
                attempt_id=attempt_id,
                student_id=student_id,
            )
        except OwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (AttemptStateError, DeliveryError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}

@router.get("/attempts/{attempt_id}/result")
def get_attempt_result(
    attempt_id: str,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.get_result(attempt_id=attempt_id, student_id=student_id)
        except GradingOwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ResultNotReadyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except GradingNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except GradingError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.get("/attempts/{attempt_id}/analysis")
def get_attempt_analysis(
    attempt_id: str,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.get_attempt_analysis(attempt_id=attempt_id, student_id=student_id)
        except GradingOwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ResultNotReadyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except GradingNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except GradingError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}


@router.post("/attempts/{attempt_id}/analysis/explain")
def explain_attempt_question(
    attempt_id: str,
    payload: AIExplainRequestSchema,
    request: Request,
    student_id: str = Depends(student_identity),
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
            data = service.explain_attempt_question(
                attempt_id=attempt_id,
                question_id=payload.question_id,
                student_id=student_id,
            )
        except AnalysisQuestionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except GradingOwnershipError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (ResultNotReadyError, DeliveryError, GradingError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"status": "success", "data": data}

