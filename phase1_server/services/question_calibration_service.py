"""Business rules for difficulty/discrimination recalibration from exam outcomes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from phase1_server.models import utc_now_iso
from phase1_server.repositories.analytics_repository import AnalyticsRepository
from phase1_server.repositories.exam_repository import ExamRepository
from phase1_server.repositories.question_recalibration_repository import (
    QuestionRecalibrationRepository,
)
from phase1_server.repositories.question_repository import QuestionRepository
from phase1_server.services.audit_service import AuditService
from phase1_server.services.exam_service import ExamNotFoundError


class QuestionCalibrationError(ValueError):
    pass


class RecalibrationRunNotFoundError(QuestionCalibrationError):
    pass


class RecalibrationRollbackError(QuestionCalibrationError):
    pass


@dataclass(frozen=True)
class QuestionRecalibrationRequest:
    min_attempts: int = 5
    apply: bool = False
    actor_id: str = "admin"


@dataclass(frozen=True)
class QuestionRecalibrationRollbackRequest:
    actor_id: str = "admin"
    reason: str | None = None


class QuestionCalibrationService:
    def __init__(
        self,
        analytics_repo: AnalyticsRepository,
        question_repo: QuestionRepository,
        exam_repo: ExamRepository,
        recalibration_repo: QuestionRecalibrationRepository | None = None,
        audit_service: AuditService | None = None,
    ):
        self._analytics_repo = analytics_repo
        self._question_repo = question_repo
        self._exam_repo = exam_repo
        self._recalibration_repo = recalibration_repo
        self._audit_service = audit_service

    def recalibrate_exam_questions(
        self,
        exam_id: str,
        request: QuestionRecalibrationRequest,
    ) -> dict:
        if request.min_attempts < 1:
            raise QuestionCalibrationError("min_attempts must be >= 1")

        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")

        run_id = str(uuid.uuid4())
        created_at = utc_now_iso()

        rows = self._analytics_repo.get_question_difficulty_heatmap(exam_id)
        items: list[dict] = []
        updated_questions = 0
        eligible_questions = 0

        for row in rows:
            question_id = row["question_id"]
            attempts = int(row["total_attempts"] or 0)
            observed_difficulty_index = float(row["difficulty_index"] or 0.0)

            suggested_level = self._suggest_difficulty_level(observed_difficulty_index)
            suggested_difficulty = self._suggest_difficulty_label(suggested_level)
            suggested_discrimination = round(
                self._suggest_discrimination_index(observed_difficulty_index),
                3,
            )

            if attempts < request.min_attempts:
                items.append(
                    {
                        "question_id": question_id,
                        "total_attempts": attempts,
                        "observed_difficulty_index": observed_difficulty_index,
                        "current": {
                            "difficulty": row["difficulty"],
                            "difficulty_level": row["difficulty_level"],
                            "discrimination_index": row["discrimination_index"],
                        },
                        "suggested": {
                            "difficulty": suggested_difficulty,
                            "difficulty_level": suggested_level,
                            "discrimination_index": suggested_discrimination,
                        },
                        "applied": False,
                        "status": "skipped_insufficient_attempts",
                    }
                )
                continue

            eligible_questions += 1
            applied = False
            status = "preview"
            if request.apply:
                applied = self._question_repo.update_question_metadata(
                    question_id,
                    {
                        "difficulty": suggested_difficulty,
                        "difficulty_level": suggested_level,
                        "discrimination_index": suggested_discrimination,
                    },
                )
                if applied:
                    updated_questions += 1
                    status = "updated"
                else:
                    status = "update_failed"

            items.append(
                {
                    "question_id": question_id,
                    "total_attempts": attempts,
                    "observed_difficulty_index": observed_difficulty_index,
                    "current": {
                        "difficulty": row["difficulty"],
                        "difficulty_level": row["difficulty_level"],
                        "discrimination_index": row["discrimination_index"],
                    },
                    "suggested": {
                        "difficulty": suggested_difficulty,
                        "difficulty_level": suggested_level,
                        "discrimination_index": suggested_discrimination,
                    },
                    "applied": applied,
                    "status": status,
                }
            )

        self._persist_run(
            run_id=run_id,
            exam_id=exam_id,
            mode="apply" if request.apply else "preview",
            min_attempts=request.min_attempts,
            total_questions=len(rows),
            eligible_questions=eligible_questions,
            updated_questions=updated_questions,
            skipped_questions=len(rows) - eligible_questions,
            triggered_by=request.actor_id,
            created_at=created_at,
            source_run_id=None,
            items=items,
        )

        response = {
            "run_id": run_id,
            "exam_id": exam_id,
            "mode": "apply" if request.apply else "preview",
            "min_attempts": request.min_attempts,
            "total_questions": len(rows),
            "eligible_questions": eligible_questions,
            "updated_questions": updated_questions,
            "skipped_questions": len(rows) - eligible_questions,
            "created_at": created_at,
            "items": items,
        }
        self._log_recalibration_event(exam_id, request, response)
        return response

    def list_recalibration_history(self, exam_id: str, limit: int = 50) -> dict:
        self._assert_exam_exists(exam_id)
        if limit < 1 or limit > 500:
            raise QuestionCalibrationError("limit must be between 1 and 500")

        repo = self._require_recalibration_repo()
        runs = repo.list_runs_by_exam(exam_id, limit=limit)
        return {"exam_id": exam_id, "runs": runs}

    def get_recalibration_run(self, exam_id: str, run_id: str) -> dict:
        self._assert_exam_exists(exam_id)
        repo = self._require_recalibration_repo()
        run = repo.get_run(run_id)
        if run is None or run["exam_id"] != exam_id:
            raise RecalibrationRunNotFoundError(
                f"Recalibration run '{run_id}' not found for exam '{exam_id}'"
            )

        items = repo.list_run_items(run_id)
        return {
            "exam_id": exam_id,
            "run": run,
            "items": [
                {
                    "question_id": item["question_id"],
                    "total_attempts": item["total_attempts"],
                    "observed_difficulty_index": item["observed_difficulty_index"],
                    "current": {
                        "difficulty": item["previous_difficulty"],
                        "difficulty_level": item["previous_difficulty_level"],
                        "discrimination_index": item["previous_discrimination_index"],
                    },
                    "suggested": {
                        "difficulty": item["suggested_difficulty"],
                        "difficulty_level": item["suggested_difficulty_level"],
                        "discrimination_index": item["suggested_discrimination_index"],
                    },
                    "applied": item["applied"],
                    "status": item["status"],
                    "created_at": item["created_at"],
                }
                for item in items
            ],
        }

    def rollback_recalibration_run(
        self,
        exam_id: str,
        run_id: str,
        request: QuestionRecalibrationRollbackRequest,
    ) -> dict:
        self._assert_exam_exists(exam_id)
        repo = self._require_recalibration_repo()
        source_run = repo.get_run(run_id)
        if source_run is None or source_run["exam_id"] != exam_id:
            raise RecalibrationRunNotFoundError(
                f"Recalibration run '{run_id}' not found for exam '{exam_id}'"
            )
        if source_run["mode"] != "apply":
            raise RecalibrationRollbackError("Only 'apply' recalibration runs can be rolled back")

        source_items = repo.list_run_items(run_id)
        if not source_items:
            raise RecalibrationRollbackError("Selected run has no item snapshots to roll back")

        rollback_run_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        rollback_items: list[dict] = []
        eligible_questions = 0
        updated_questions = 0

        for source_item in source_items:
            question_id = source_item["question_id"]
            restore_difficulty = source_item["previous_difficulty"]
            restore_level = source_item["previous_difficulty_level"]
            restore_discrimination = source_item["previous_discrimination_index"]

            current_row = self._question_repo.get_question_with_options(question_id)
            current_question = None if current_row is None else current_row[0]

            if not source_item["applied"] or source_item["status"] not in {"updated", "rolled_back"}:
                rollback_items.append(
                    {
                        "question_id": question_id,
                        "total_attempts": source_item["total_attempts"],
                        "observed_difficulty_index": source_item["observed_difficulty_index"],
                        "current": {
                            "difficulty": None if current_question is None else current_question.difficulty,
                            "difficulty_level": (
                                None if current_question is None else current_question.difficulty_level
                            ),
                            "discrimination_index": (
                                None
                                if current_question is None
                                else current_question.discrimination_index
                            ),
                        },
                        "suggested": {
                            "difficulty": restore_difficulty,
                            "difficulty_level": restore_level,
                            "discrimination_index": restore_discrimination,
                        },
                        "applied": False,
                        "status": "skipped_not_previously_updated",
                    }
                )
                continue

            if current_question is None:
                rollback_items.append(
                    {
                        "question_id": question_id,
                        "total_attempts": source_item["total_attempts"],
                        "observed_difficulty_index": source_item["observed_difficulty_index"],
                        "current": {
                            "difficulty": None,
                            "difficulty_level": None,
                            "discrimination_index": None,
                        },
                        "suggested": {
                            "difficulty": restore_difficulty,
                            "difficulty_level": restore_level,
                            "discrimination_index": restore_discrimination,
                        },
                        "applied": False,
                        "status": "skipped_missing_question",
                    }
                )
                continue

            eligible_questions += 1
            applied = self._question_repo.update_question_metadata(
                question_id,
                {
                    "difficulty": restore_difficulty,
                    "difficulty_level": restore_level,
                    "discrimination_index": restore_discrimination,
                },
            )
            if applied:
                updated_questions += 1

            rollback_items.append(
                {
                    "question_id": question_id,
                    "total_attempts": source_item["total_attempts"],
                    "observed_difficulty_index": source_item["observed_difficulty_index"],
                    "current": {
                        "difficulty": current_question.difficulty,
                        "difficulty_level": current_question.difficulty_level,
                        "discrimination_index": current_question.discrimination_index,
                    },
                    "suggested": {
                        "difficulty": restore_difficulty,
                        "difficulty_level": restore_level,
                        "discrimination_index": restore_discrimination,
                    },
                    "applied": applied,
                    "status": "rolled_back" if applied else "rollback_failed",
                }
            )

        self._persist_run(
            run_id=rollback_run_id,
            exam_id=exam_id,
            mode="rollback",
            min_attempts=source_run["min_attempts"],
            total_questions=len(source_items),
            eligible_questions=eligible_questions,
            updated_questions=updated_questions,
            skipped_questions=len(source_items) - eligible_questions,
            triggered_by=request.actor_id,
            created_at=created_at,
            source_run_id=run_id,
            items=rollback_items,
        )

        response = {
            "run_id": rollback_run_id,
            "source_run_id": run_id,
            "exam_id": exam_id,
            "mode": "rollback",
            "min_attempts": source_run["min_attempts"],
            "total_questions": len(source_items),
            "eligible_questions": eligible_questions,
            "updated_questions": updated_questions,
            "skipped_questions": len(source_items) - eligible_questions,
            "created_at": created_at,
            "reason": request.reason,
            "items": rollback_items,
        }
        self._log_rollback_event(exam_id, request, response)
        return response

    def _persist_run(
        self,
        run_id: str,
        exam_id: str,
        mode: str,
        min_attempts: int | None,
        total_questions: int,
        eligible_questions: int,
        updated_questions: int,
        skipped_questions: int,
        triggered_by: str,
        created_at: str,
        source_run_id: str | None,
        items: list[dict],
    ) -> None:
        repo = self._recalibration_repo
        if repo is None:
            return

        repo.create_run(
            run_id=run_id,
            exam_id=exam_id,
            mode=mode,
            min_attempts=min_attempts,
            total_questions=total_questions,
            eligible_questions=eligible_questions,
            updated_questions=updated_questions,
            skipped_questions=skipped_questions,
            triggered_by=triggered_by,
            created_at=created_at,
            source_run_id=source_run_id,
        )
        repo.create_run_items(
            run_id=run_id,
            items=[
                {
                    "question_id": item["question_id"],
                    "total_attempts": item["total_attempts"],
                    "observed_difficulty_index": item["observed_difficulty_index"],
                    "previous_difficulty": item["current"]["difficulty"],
                    "previous_difficulty_level": item["current"]["difficulty_level"],
                    "previous_discrimination_index": item["current"]["discrimination_index"],
                    "suggested_difficulty": item["suggested"]["difficulty"],
                    "suggested_difficulty_level": item["suggested"]["difficulty_level"],
                    "suggested_discrimination_index": item["suggested"]["discrimination_index"],
                    "applied": item["applied"],
                    "status": item["status"],
                }
                for item in items
            ],
            created_at=created_at,
        )

    def _log_rollback_event(
        self,
        exam_id: str,
        request: QuestionRecalibrationRollbackRequest,
        response: dict,
    ) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.log_event(
                entity_type="exam",
                entity_id=exam_id,
                actor_type="admin",
                actor_id=request.actor_id,
                event_type="QUESTION_DIFFICULTY_RECALIBRATION_ROLLED_BACK",
                payload={
                    "run_id": response["run_id"],
                    "source_run_id": response["source_run_id"],
                    "updated_questions": response["updated_questions"],
                    "eligible_questions": response["eligible_questions"],
                    "reason": request.reason,
                },
            )
        except Exception:
            return

    def _log_recalibration_event(
        self,
        exam_id: str,
        request: QuestionRecalibrationRequest,
        response: dict,
    ) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.log_event(
                entity_type="exam",
                entity_id=exam_id,
                actor_type="admin",
                actor_id=request.actor_id,
                event_type="QUESTION_DIFFICULTY_RECALIBRATED",
                payload={
                    "run_id": response["run_id"],
                    "mode": response["mode"],
                    "min_attempts": response["min_attempts"],
                    "total_questions": response["total_questions"],
                    "eligible_questions": response["eligible_questions"],
                    "updated_questions": response["updated_questions"],
                    "skipped_questions": response["skipped_questions"],
                },
            )
        except Exception:
            return

    def _assert_exam_exists(self, exam_id: str) -> None:
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")

    def _require_recalibration_repo(self) -> QuestionRecalibrationRepository:
        if self._recalibration_repo is None:
            raise QuestionCalibrationError("Recalibration history storage is unavailable")
        return self._recalibration_repo

    @staticmethod
    def _suggest_difficulty_level(observed_difficulty_index: float) -> int:
        clamped = max(0.0, min(100.0, observed_difficulty_index))
        level = 10 - int(clamped // 10)
        return min(max(level, 1), 10)

    @staticmethod
    def _suggest_difficulty_label(level: int) -> str:
        if level <= 3:
            return "easy"
        if level <= 7:
            return "medium"
        return "hard"

    @staticmethod
    def _suggest_discrimination_index(observed_difficulty_index: float) -> float:
        clamped = max(0.0, min(100.0, observed_difficulty_index))
        return max(0.0, 1.0 - abs(clamped - 50.0) / 50.0)
