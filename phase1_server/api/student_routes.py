"""Student routes for exam delivery flow."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from phase1_server.api.deps import student_identity
from phase1_server.schemas import AnswerSubmitSchema
from phase1_server.services.audit_service import AuditService
from phase1_server.services.delivery_service import (
    AnswerSubmissionPayload,
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
from phase1_server.services.exam_service import ExamNotFoundError, ExamValidationError
from phase1_server.uow import UnitOfWork

router = APIRouter(prefix="/student", tags=["student"])


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

