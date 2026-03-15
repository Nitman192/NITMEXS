"""Repository for attempt persistence."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Protocol

from phase1_server.models import Attempt, AttemptResponse, AttemptStatus


class AttemptRepository(Protocol):
    def get(self, attempt_id: str) -> Attempt | None: ...

    def create(self, attempt: Attempt) -> None: ...

    def update_status(
        self,
        attempt_id: str,
        status: AttemptStatus,
        updated_at: str,
        submitted_at: str | None,
        expected_version: int,
    ) -> bool: ...

    def update_timer_state(
        self,
        attempt_id: str,
        *,
        timer_frozen: bool,
        timer_paused_at: str | None,
        expires_at: str | None = None,
    ) -> None: ...

    def get_by_candidate_and_exam(
        self,
        candidate_id: str,
        exam_id: str,
    ) -> Attempt | None: ...

    def get_snapshot_question_id(self, attempt_id: str, order_index: int) -> str | None: ...

    def list_snapshot_question_ids(self, attempt_id: str) -> list[str]: ...

    def question_in_snapshot(self, attempt_id: str, question_id: str) -> bool: ...

    def upsert_response(self, response: AttemptResponse) -> None: ...

    def get_responses(self, attempt_id: str) -> dict[str, dict]: ...

    def clear_results(self, attempt_id: str) -> None: ...

    def save_attempt_result(
        self,
        attempt_id: str,
        total_score: float,
        total_possible_marks: float,
        percentage: float,
        passed: bool,
        graded_at: str,
    ) -> None: ...

    def save_question_result(
        self,
        attempt_id: str,
        question_id: str,
        question_type: str,
        selected_option_id: str | None,
        correct_option_id: str | None,
        text_answer: str | None,
        matched_variant_id: str | None,
        grading_state: str,
        marks_awarded: float,
        max_marks: float,
        is_correct: bool,
        reviewed_by: str | None = None,
        reviewed_at: str | None = None,
        review_note: str | None = None,
    ) -> None: ...

    def get_attempt_result(self, attempt_id: str) -> dict | None: ...

    def result_exists(self, attempt_id: str) -> bool: ...

    def get_question_results(self, attempt_id: str) -> list[dict]: ...

    def get_question_result(self, attempt_id: str, question_id: str) -> dict | None: ...

    def update_question_result_review(
        self,
        attempt_id: str,
        question_id: str,
        grading_state: str,
        marks_awarded: float,
        is_correct: bool,
        matched_variant_id: str | None,
        reviewed_by: str | None,
        reviewed_at: str | None,
        review_note: str | None,
    ) -> None: ...

    def count_pending_question_results(self, attempt_id: str) -> int: ...

    def delete_attempt_result(self, attempt_id: str) -> None: ...

    def list_fib_review_queue(self, exam_id: str) -> list[dict]: ...

    def list_subjective_review_queue(self, exam_id: str) -> list[dict]: ...

    def list_attempt_ids_for_pending_fib_variant(
        self,
        exam_id: str,
        question_id: str,
        normalized_text_answer: str,
    ) -> list[dict]: ...

    def log_audit_event(
        self,
        attempt_id: str,
        event_type: str,
        timestamp: str,
        actor_id: str,
        actor_role: str,
    ) -> None: ...

    def list_audit_events(self, attempt_id: str) -> list[dict]: ...

    def is_expired(self, attempt_id: str, now_iso: str) -> bool: ...

    def list_active_attempts_by_exam(self, exam_id: str) -> list[dict]: ...

    def list_active_attempts(self, limit: int = 200) -> list[dict]: ...

    def list_recent_finalize_events(self, exam_id: str, limit: int = 20) -> list[dict]: ...

    def list_recent_finalize_events_global(self, limit: int = 50) -> list[dict]: ...

    def list_attempt_events(
        self,
        limit: int = 100,
        since: str | None = None,
        exam_id: str | None = None,
        cursor_event_id: str | None = None,
    ) -> list[dict]: ...

    def list_expired_active_attempt_ids(
        self,
        now_iso: str,
        exam_id: str | None = None,
        limit: int = 500,
    ) -> list[str]: ...

    def list_attempt_ids_by_exam_and_status(
        self,
        exam_id: str,
        status: AttemptStatus,
        limit: int = 1000,
    ) -> list[str]: ...

    def get_exam_question_analytics(self, exam_id: str) -> list[dict]: ...

    def get_exam_attempt_scores(self, exam_id: str) -> list[dict]: ...

    def count_pending_reviews_by_exam(self, exam_id: str) -> int: ...

    def count_ready_results_by_exam(self, exam_id: str) -> int: ...

    def list_exam_results(self, exam_id: str) -> list[dict]: ...


class SQLiteAttemptRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get(self, attempt_id: str) -> Attempt | None:
        row = self._conn.execute(
            """
            SELECT id, candidate_id, exam_id, status, created_at, updated_at, version, submitted_at, expires_at,
                   timer_frozen, timer_paused_at
            FROM attempts
            WHERE id = ?
            """,
            (attempt_id,),
        ).fetchone()
        if not row:
            return None
        return Attempt(
            id=row["id"],
            candidate_id=row["candidate_id"],
            exam_id=row["exam_id"],
            status=AttemptStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=row["version"],
            submitted_at=row["submitted_at"],
            expires_at=row["expires_at"],
            timer_frozen=bool(row["timer_frozen"]),
            timer_paused_at=row["timer_paused_at"],
        )

    def create(self, attempt: Attempt) -> None:
        self._conn.execute(
            """
            INSERT INTO attempts(
                id, candidate_id, exam_id, status, created_at, updated_at, version, submitted_at, expires_at,
                timer_frozen, timer_paused_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt.id,
                attempt.candidate_id,
                attempt.exam_id,
                attempt.status.value,
                attempt.created_at,
                attempt.updated_at,
                attempt.version,
                attempt.submitted_at,
                attempt.expires_at,
                1 if attempt.timer_frozen else 0,
                attempt.timer_paused_at,
            ),
        )

    def update_status(
        self,
        attempt_id: str,
        status: AttemptStatus,
        updated_at: str,
        submitted_at: str | None,
        expected_version: int,
    ) -> bool:
        cursor = self._conn.execute(
            """
            UPDATE attempts
            SET status = ?,
                updated_at = ?,
                submitted_at = COALESCE(?, submitted_at),
                version = version + 1
            WHERE id = ? AND version = ?
            """,
            (status.value, updated_at, submitted_at, attempt_id, expected_version),
        )
        return cursor.rowcount == 1

    def get_by_candidate_and_exam(
        self,
        candidate_id: str,
        exam_id: str,
    ) -> Attempt | None:
        row = self._conn.execute(
            """
            SELECT id, candidate_id, exam_id, status, created_at, updated_at, version, submitted_at, expires_at,
                   timer_frozen, timer_paused_at
            FROM attempts
            WHERE candidate_id = ? AND exam_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (candidate_id, exam_id),
        ).fetchone()
        if not row:
            return None
        return Attempt(
            id=row["id"],
            candidate_id=row["candidate_id"],
            exam_id=row["exam_id"],
            status=AttemptStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=row["version"],
            submitted_at=row["submitted_at"],
            expires_at=row["expires_at"],
            timer_frozen=bool(row["timer_frozen"]),
            timer_paused_at=row["timer_paused_at"],
        )

    def update_timer_state(
        self,
        attempt_id: str,
        *,
        timer_frozen: bool,
        timer_paused_at: str | None,
        expires_at: str | None = None,
    ) -> None:
        if expires_at is None:
            self._conn.execute(
                """
                UPDATE attempts
                SET timer_frozen = ?, timer_paused_at = ?
                WHERE id = ?
                """,
                (1 if timer_frozen else 0, timer_paused_at, attempt_id),
            )
            return
        self._conn.execute(
            """
            UPDATE attempts
            SET timer_frozen = ?, timer_paused_at = ?, expires_at = ?
            WHERE id = ?
            """,
            (1 if timer_frozen else 0, timer_paused_at, expires_at, attempt_id),
        )

    def get_snapshot_question_id(self, attempt_id: str, order_index: int) -> str | None:
        row = self._conn.execute(
            """
            SELECT question_id
            FROM attempt_question_snapshots
            WHERE attempt_id = ? AND order_index = ?
            """,
            (attempt_id, order_index),
        ).fetchone()
        return None if row is None else row["question_id"]

    def list_snapshot_question_ids(self, attempt_id: str) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT question_id
            FROM attempt_question_snapshots
            WHERE attempt_id = ?
            ORDER BY order_index ASC
            """,
            (attempt_id,),
        ).fetchall()
        return [row["question_id"] for row in rows]

    def question_in_snapshot(self, attempt_id: str, question_id: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1
            FROM attempt_question_snapshots
            WHERE attempt_id = ? AND question_id = ?
            LIMIT 1
            """,
            (attempt_id, question_id),
        ).fetchone()
        return row is not None

    def upsert_response(self, response: AttemptResponse) -> None:
        self._conn.execute(
            """
            INSERT INTO attempt_responses(
                attempt_id, question_id, selected_option_id, text_answer,
                normalized_text_answer, word_count, answered_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(attempt_id, question_id)
            DO UPDATE SET selected_option_id = excluded.selected_option_id,
                          text_answer = excluded.text_answer,
                          normalized_text_answer = excluded.normalized_text_answer,
                          word_count = excluded.word_count,
                          answered_at = excluded.answered_at
            """,
            (
                response.attempt_id,
                response.question_id,
                response.selected_option_id,
                response.text_answer,
                response.normalized_text_answer,
                response.word_count,
                response.answered_at,
            ),
        )

    def get_responses(self, attempt_id: str) -> dict[str, dict]:
        rows = self._conn.execute(
            """
            SELECT question_id, selected_option_id, text_answer, normalized_text_answer, word_count, answered_at
            FROM attempt_responses
            WHERE attempt_id = ?
            """,
            (attempt_id,),
        ).fetchall()
        return {
            row["question_id"]: {
                "selected_option_id": row["selected_option_id"],
                "text_answer": row["text_answer"],
                "normalized_text_answer": row["normalized_text_answer"],
                "word_count": row["word_count"],
                "answered_at": row["answered_at"],
            }
            for row in rows
        }

    def clear_results(self, attempt_id: str) -> None:
        self._conn.execute(
            "DELETE FROM attempt_question_results WHERE attempt_id = ?",
            (attempt_id,),
        )
        self._conn.execute(
            "DELETE FROM attempt_results WHERE attempt_id = ?",
            (attempt_id,),
        )

    def save_attempt_result(
        self,
        attempt_id: str,
        total_score: float,
        total_possible_marks: float,
        percentage: float,
        passed: bool,
        graded_at: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO attempt_results(
                attempt_id, total_score, total_possible_marks, percentage, passed, graded_at
            ) VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                total_score,
                total_possible_marks,
                percentage,
                1 if passed else 0,
                graded_at,
            ),
        )

    def save_question_result(
        self,
        attempt_id: str,
        question_id: str,
        question_type: str,
        selected_option_id: str | None,
        correct_option_id: str | None,
        text_answer: str | None,
        matched_variant_id: str | None,
        grading_state: str,
        marks_awarded: float,
        max_marks: float,
        is_correct: bool,
        reviewed_by: str | None = None,
        reviewed_at: str | None = None,
        review_note: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO attempt_question_results(
                attempt_id, question_id, question_type, selected_option_id, correct_option_id,
                text_answer, matched_variant_id, grading_state,
                marks_awarded, max_marks, is_correct, reviewed_by, reviewed_at, review_note
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                question_id,
                question_type,
                selected_option_id,
                correct_option_id,
                text_answer,
                matched_variant_id,
                grading_state,
                marks_awarded,
                max_marks,
                1 if is_correct else 0,
                reviewed_by,
                reviewed_at,
                review_note,
            ),
        )

    def get_attempt_result(self, attempt_id: str) -> dict | None:
        row = self._conn.execute(
            """
            SELECT attempt_id, total_score, total_possible_marks, percentage, passed, graded_at
            FROM attempt_results
            WHERE attempt_id = ?
            """,
            (attempt_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "attempt_id": row["attempt_id"],
            "total_score": row["total_score"],
            "total_possible_marks": row["total_possible_marks"],
            "percentage": row["percentage"],
            "passed": bool(row["passed"]),
            "graded_at": row["graded_at"],
        }

    def result_exists(self, attempt_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM attempt_results WHERE attempt_id = ? LIMIT 1",
            (attempt_id,),
        ).fetchone()
        return row is not None

    def get_question_results(self, attempt_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT attempt_id, question_id, question_type, selected_option_id, correct_option_id,
                   text_answer, matched_variant_id, grading_state,
                   marks_awarded, max_marks, is_correct, reviewed_by, reviewed_at, review_note
            FROM attempt_question_results
            WHERE attempt_id = ?
            ORDER BY question_id ASC
            """,
            (attempt_id,),
        ).fetchall()
        return [
            {
                "attempt_id": row["attempt_id"],
                "question_id": row["question_id"],
                "question_type": row["question_type"],
                "selected_option_id": row["selected_option_id"],
                "correct_option_id": row["correct_option_id"],
                "text_answer": row["text_answer"],
                "matched_variant_id": row["matched_variant_id"],
                "grading_state": row["grading_state"],
                "marks_awarded": row["marks_awarded"],
                "max_marks": row["max_marks"],
                "is_correct": bool(row["is_correct"]),
                "reviewed_by": row["reviewed_by"],
                "reviewed_at": row["reviewed_at"],
                "review_note": row["review_note"],
            }
            for row in rows
        ]

    def get_question_result(self, attempt_id: str, question_id: str) -> dict | None:
        row = self._conn.execute(
            """
            SELECT attempt_id, question_id, question_type, selected_option_id, correct_option_id,
                   text_answer, matched_variant_id, grading_state,
                   marks_awarded, max_marks, is_correct, reviewed_by, reviewed_at, review_note
            FROM attempt_question_results
            WHERE attempt_id = ? AND question_id = ?
            """,
            (attempt_id, question_id),
        ).fetchone()
        if row is None:
            return None
        return {
            "attempt_id": row["attempt_id"],
            "question_id": row["question_id"],
            "question_type": row["question_type"],
            "selected_option_id": row["selected_option_id"],
            "correct_option_id": row["correct_option_id"],
            "text_answer": row["text_answer"],
            "matched_variant_id": row["matched_variant_id"],
            "grading_state": row["grading_state"],
            "marks_awarded": row["marks_awarded"],
            "max_marks": row["max_marks"],
            "is_correct": bool(row["is_correct"]),
            "reviewed_by": row["reviewed_by"],
            "reviewed_at": row["reviewed_at"],
            "review_note": row["review_note"],
        }

    def update_question_result_review(
        self,
        attempt_id: str,
        question_id: str,
        grading_state: str,
        marks_awarded: float,
        is_correct: bool,
        matched_variant_id: str | None,
        reviewed_by: str | None,
        reviewed_at: str | None,
        review_note: str | None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE attempt_question_results
            SET grading_state = ?,
                marks_awarded = ?,
                is_correct = ?,
                matched_variant_id = COALESCE(?, matched_variant_id),
                reviewed_by = ?,
                reviewed_at = ?,
                review_note = ?
            WHERE attempt_id = ? AND question_id = ?
            """,
            (
                grading_state,
                marks_awarded,
                1 if is_correct else 0,
                matched_variant_id,
                reviewed_by,
                reviewed_at,
                review_note,
                attempt_id,
                question_id,
            ),
        )

    def count_pending_question_results(self, attempt_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM attempt_question_results
            WHERE attempt_id = ? AND grading_state = 'pending_review'
            """,
            (attempt_id,),
        ).fetchone()
        return 0 if row is None else int(row["total"] or 0)

    def delete_attempt_result(self, attempt_id: str) -> None:
        self._conn.execute(
            "DELETE FROM attempt_results WHERE attempt_id = ?",
            (attempt_id,),
        )

    def log_audit_event(
        self,
        attempt_id: str,
        event_type: str,
        timestamp: str,
        actor_id: str,
        actor_role: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO audit_logs(id, attempt_id, event_type, timestamp, actor_id, actor_role)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), attempt_id, event_type, timestamp, actor_id, actor_role),
        )

    def list_audit_events(self, attempt_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT id, attempt_id, event_type, timestamp, actor_id, actor_role
            FROM audit_logs
            WHERE attempt_id = ?
            ORDER BY timestamp ASC
            """,
            (attempt_id,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "attempt_id": row["attempt_id"],
                "event_type": row["event_type"],
                "timestamp": row["timestamp"],
                "actor_id": row["actor_id"],
                "actor_role": row["actor_role"],
            }
            for row in rows
        ]

    def is_expired(self, attempt_id: str, now_iso: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1
            FROM attempts
            WHERE id = ? AND expires_at IS NOT NULL AND expires_at < ?
            LIMIT 1
            """,
            (attempt_id, now_iso),
        ).fetchone()
        return row is not None

    def list_active_attempts_by_exam(self, exam_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT
                a.id AS attempt_id,
                a.candidate_id AS student_id,
                a.exam_id AS exam_id,
                a.created_at AS started_at,
                a.updated_at AS updated_at,
                a.expires_at AS expires_at,
                a.version AS version,
                COUNT(DISTINCT ar.question_id) AS answered_count,
                COUNT(DISTINCT s.question_id) AS total_questions
            FROM attempts a
            LEFT JOIN attempt_responses ar
                ON ar.attempt_id = a.id
            LEFT JOIN attempt_question_snapshots s
                ON s.attempt_id = a.id
            WHERE a.exam_id = ? AND a.status = ?
            GROUP BY
                a.id, a.candidate_id, a.exam_id, a.created_at, a.updated_at, a.expires_at, a.version
            ORDER BY a.created_at ASC
            """,
            (exam_id, AttemptStatus.ACTIVE.value),
        ).fetchall()
        return [
            {
                "attempt_id": row["attempt_id"],
                "student_id": row["student_id"],
                "exam_id": row["exam_id"],
                "started_at": row["started_at"],
                "updated_at": row["updated_at"],
                "expires_at": row["expires_at"],
                "version": int(row["version"]),
                "answered_count": int(row["answered_count"] or 0),
                "total_questions": int(row["total_questions"] or 0),
            }
            for row in rows
        ]

    def list_active_attempts(self, limit: int = 200) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT
                a.id AS attempt_id,
                a.candidate_id AS student_id,
                a.exam_id AS exam_id,
                a.created_at AS started_at,
                a.updated_at AS updated_at,
                a.expires_at AS expires_at,
                a.version AS version,
                COUNT(DISTINCT ar.question_id) AS answered_count,
                COUNT(DISTINCT s.question_id) AS total_questions
            FROM attempts a
            LEFT JOIN attempt_responses ar
                ON ar.attempt_id = a.id
            LEFT JOIN attempt_question_snapshots s
                ON s.attempt_id = a.id
            WHERE a.status = ?
            GROUP BY
                a.id, a.candidate_id, a.exam_id, a.created_at, a.updated_at, a.expires_at, a.version
            ORDER BY a.created_at ASC
            LIMIT ?
            """,
            (AttemptStatus.ACTIVE.value, limit),
        ).fetchall()
        return [
            {
                "attempt_id": row["attempt_id"],
                "student_id": row["student_id"],
                "exam_id": row["exam_id"],
                "started_at": row["started_at"],
                "updated_at": row["updated_at"],
                "expires_at": row["expires_at"],
                "version": int(row["version"]),
                "answered_count": int(row["answered_count"] or 0),
                "total_questions": int(row["total_questions"] or 0),
            }
            for row in rows
        ]

    def list_recent_finalize_events(self, exam_id: str, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT
                ae.entity_id AS attempt_id,
                a.candidate_id AS student_id,
                ae.actor_type AS actor_type,
                ae.actor_id AS actor_id,
                ae.created_at AS created_at
            FROM audit_events ae
            INNER JOIN attempts a
                ON a.id = ae.entity_id
            WHERE
                ae.entity_type = 'attempt'
                AND ae.event_type = 'FINALIZED'
                AND a.exam_id = ?
            ORDER BY ae.created_at DESC
            LIMIT ?
            """,
            (exam_id, limit),
        ).fetchall()
        return [
            {
                "attempt_id": row["attempt_id"],
                "student_id": row["student_id"],
                "exam_id": exam_id,
                "actor_type": row["actor_type"],
                "actor_id": row["actor_id"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def list_recent_finalize_events_global(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT
                ae.entity_id AS attempt_id,
                a.candidate_id AS student_id,
                a.exam_id AS exam_id,
                ae.actor_type AS actor_type,
                ae.actor_id AS actor_id,
                ae.created_at AS created_at
            FROM audit_events ae
            INNER JOIN attempts a
                ON a.id = ae.entity_id
            WHERE
                ae.entity_type = 'attempt'
                AND ae.event_type = 'FINALIZED'
            ORDER BY ae.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "attempt_id": row["attempt_id"],
                "student_id": row["student_id"],
                "exam_id": row["exam_id"],
                "actor_type": row["actor_type"],
                "actor_id": row["actor_id"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def list_attempt_events(
        self,
        limit: int = 100,
        since: str | None = None,
        exam_id: str | None = None,
        cursor_event_id: str | None = None,
    ) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT
                ae.id AS event_id,
                ae.created_at AS created_at,
                ae.event_type AS event_type,
                ae.entity_id AS attempt_id,
                ae.actor_type AS actor_type,
                ae.actor_id AS actor_id,
                ae.payload_json AS payload_json,
                a.exam_id AS exam_id,
                a.candidate_id AS student_id
            FROM audit_events ae
            INNER JOIN attempts a
                ON a.id = ae.entity_id
            WHERE
                ae.entity_type = 'attempt'
                AND (? IS NULL OR a.exam_id = ?)
                AND (
                    ? IS NULL
                    OR ae.created_at > ?
                    OR (
                        ae.created_at = ?
                        AND ? IS NOT NULL
                        AND ae.id > ?
                    )
                )
            ORDER BY ae.created_at ASC, ae.id ASC
            LIMIT ?
            """,
            (
                exam_id,
                exam_id,
                since,
                since,
                since,
                cursor_event_id,
                cursor_event_id,
                limit,
            ),
        ).fetchall()

        result: list[dict] = []
        for row in rows:
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except json.JSONDecodeError:
                payload = {}
            result.append(
                {
                    "event_id": row["event_id"],
                    "created_at": row["created_at"],
                    "event_type": row["event_type"],
                    "attempt_id": row["attempt_id"],
                    "exam_id": row["exam_id"],
                    "student_id": row["student_id"],
                    "actor_type": row["actor_type"],
                    "actor_id": row["actor_id"],
                    "payload": payload,
                }
            )
        return result

    def get_exam_question_analytics(self, exam_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT
                aqr.question_id AS question_id,
                COUNT(*) AS total_attempts,
                SUM(CASE WHEN aqr.is_correct = 1 THEN 1 ELSE 0 END) AS correct_count,
                AVG(aqr.marks_awarded) AS average_score
            FROM attempt_question_results aqr
            INNER JOIN attempts a ON a.id = aqr.attempt_id
            WHERE a.exam_id = ?
            GROUP BY aqr.question_id
            ORDER BY aqr.question_id ASC
            """,
            (exam_id,),
        ).fetchall()
        result = []
        for row in rows:
            total_attempts = int(row["total_attempts"])
            correct_count = int(row["correct_count"] or 0)
            difficulty_index = (
                (correct_count / total_attempts) * 100.0 if total_attempts > 0 else 0.0
            )
            result.append(
                {
                    "question_id": row["question_id"],
                    "total_attempts": total_attempts,
                    "average_score": float(row["average_score"] or 0.0),
                    "difficulty_index": difficulty_index,
                }
            )
        return result

    def get_exam_attempt_scores(self, exam_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT ar.attempt_id, ar.total_score, ar.passed
            FROM attempt_results ar
            INNER JOIN attempts a ON a.id = ar.attempt_id
            WHERE a.exam_id = ?
            ORDER BY ar.attempt_id ASC
            """,
            (exam_id,),
        ).fetchall()
        return [
            {
                "attempt_id": row["attempt_id"],
                "total_score": float(row["total_score"]),
                "passed": bool(row["passed"]),
            }
            for row in rows
        ]

    def count_pending_reviews_by_exam(self, exam_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM attempt_question_results aqr
            INNER JOIN attempts a ON a.id = aqr.attempt_id
            WHERE a.exam_id = ? AND aqr.grading_state = 'pending_review'
            """,
            (exam_id,),
        ).fetchone()
        return 0 if row is None else int(row["total"] or 0)

    def count_ready_results_by_exam(self, exam_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM attempt_results ar
            INNER JOIN attempts a ON a.id = ar.attempt_id
            WHERE a.exam_id = ?
            """,
            (exam_id,),
        ).fetchone()
        return 0 if row is None else int(row["total"] or 0)

    def list_exam_results(self, exam_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT
                a.id AS attempt_id,
                a.candidate_id AS student_id,
                COALESCE(sa.display_name, a.candidate_id) AS display_name,
                a.status AS attempt_status,
                a.submitted_at AS submitted_at,
                ar.total_score AS total_score,
                ar.total_possible_marks AS total_possible_marks,
                ar.percentage AS percentage,
                ar.passed AS passed,
                ar.graded_at AS graded_at,
                COALESCE((
                    SELECT COUNT(*)
                    FROM attempt_question_results pending
                    WHERE pending.attempt_id = a.id
                      AND pending.grading_state = 'pending_review'
                ), 0) AS pending_review_count
            FROM attempts a
            LEFT JOIN attempt_results ar
                ON ar.attempt_id = a.id
            LEFT JOIN student_accounts sa
                ON sa.student_id = a.candidate_id
            WHERE a.exam_id = ?
            ORDER BY a.created_at DESC, a.candidate_id ASC
            """,
            (exam_id,),
        ).fetchall()
        return [
            {
                "attempt_id": row["attempt_id"],
                "student_id": row["student_id"],
                "display_name": row["display_name"],
                "attempt_status": row["attempt_status"],
                "submitted_at": row["submitted_at"],
                "total_score": None if row["total_score"] is None else float(row["total_score"]),
                "total_possible_marks": None if row["total_possible_marks"] is None else float(row["total_possible_marks"]),
                "percentage": None if row["percentage"] is None else float(row["percentage"]),
                "passed": None if row["passed"] is None else bool(row["passed"]),
                "graded_at": row["graded_at"],
                "pending_review_count": int(row["pending_review_count"] or 0),
            }
            for row in rows
        ]

    def list_expired_active_attempt_ids(
        self,
        now_iso: str,
        exam_id: str | None = None,
        limit: int = 500,
    ) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT id
            FROM attempts
            WHERE
                status IN (?, ?)
                AND expires_at IS NOT NULL
                AND expires_at < ?
                AND (? IS NULL OR exam_id = ?)
            ORDER BY expires_at ASC
            LIMIT ?
            """,
            (
                AttemptStatus.ACTIVE.value,
                AttemptStatus.PAUSED.value,
                now_iso,
                exam_id,
                exam_id,
                limit,
            ),
        ).fetchall()
        return [row["id"] for row in rows]

    def list_fib_review_queue(self, exam_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT
                q.id AS question_id,
                q.text AS question_text,
                q.marks AS max_marks,
                ar.normalized_text_answer AS normalized_text_answer,
                MIN(ar.text_answer) AS sample_answer,
                COUNT(*) AS submission_count,
                GROUP_CONCAT(DISTINCT a.id) AS attempt_ids,
                GROUP_CONCAT(DISTINCT a.candidate_id) AS student_ids
            FROM attempt_question_results aqr
            INNER JOIN attempts a ON a.id = aqr.attempt_id
            INNER JOIN questions q ON q.id = aqr.question_id
            INNER JOIN attempt_responses ar
                ON ar.attempt_id = aqr.attempt_id AND ar.question_id = aqr.question_id
            WHERE
                a.exam_id = ?
                AND q.question_type = 'fib_text'
                AND aqr.grading_state = 'pending_review'
            GROUP BY q.id, q.text, q.marks, ar.normalized_text_answer
            ORDER BY q.id ASC, submission_count DESC, ar.normalized_text_answer ASC
            """,
            (exam_id,),
        ).fetchall()
        return [
            {
                "question_id": row["question_id"],
                "question_text": row["question_text"],
                "max_marks": float(row["max_marks"]),
                "normalized_text_answer": row["normalized_text_answer"],
                "sample_answer": row["sample_answer"],
                "submission_count": int(row["submission_count"] or 0),
                "attempt_ids": (row["attempt_ids"] or "").split(",") if row["attempt_ids"] else [],
                "student_ids": (row["student_ids"] or "").split(",") if row["student_ids"] else [],
            }
            for row in rows
        ]

    def list_subjective_review_queue(self, exam_id: str) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT
                a.id AS attempt_id,
                a.candidate_id AS student_id,
                q.id AS question_id,
                q.text AS question_text,
                q.question_type AS question_type,
                q.marks AS max_marks,
                q.word_target_min AS word_target_min,
                q.word_target_max AS word_target_max,
                q.word_hard_max AS word_hard_max,
                ar.text_answer AS text_answer,
                ar.word_count AS word_count,
                aqr.grading_state AS grading_state
            FROM attempt_question_results aqr
            INNER JOIN attempts a ON a.id = aqr.attempt_id
            INNER JOIN questions q ON q.id = aqr.question_id
            INNER JOIN attempt_responses ar
                ON ar.attempt_id = aqr.attempt_id AND ar.question_id = aqr.question_id
            WHERE
                a.exam_id = ?
                AND q.question_type IN ('short_answer', 'long_answer')
                AND aqr.grading_state = 'pending_review'
            ORDER BY q.id ASC, a.candidate_id ASC
            """,
            (exam_id,),
        ).fetchall()
        return [
            {
                "attempt_id": row["attempt_id"],
                "student_id": row["student_id"],
                "question_id": row["question_id"],
                "question_text": row["question_text"],
                "question_type": row["question_type"],
                "max_marks": float(row["max_marks"]),
                "word_target_min": row["word_target_min"],
                "word_target_max": row["word_target_max"],
                "word_hard_max": row["word_hard_max"],
                "text_answer": row["text_answer"],
                "word_count": row["word_count"],
                "grading_state": row["grading_state"],
            }
            for row in rows
        ]

    def list_attempt_ids_for_pending_fib_variant(
        self,
        exam_id: str,
        question_id: str,
        normalized_text_answer: str,
    ) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT
                a.id AS attempt_id,
                a.candidate_id AS student_id,
                ar.text_answer AS text_answer
            FROM attempt_question_results aqr
            INNER JOIN attempts a ON a.id = aqr.attempt_id
            INNER JOIN attempt_responses ar
                ON ar.attempt_id = aqr.attempt_id AND ar.question_id = aqr.question_id
            WHERE
                a.exam_id = ?
                AND aqr.question_id = ?
                AND aqr.grading_state = 'pending_review'
                AND ar.normalized_text_answer = ?
            ORDER BY a.created_at ASC
            """,
            (exam_id, question_id, normalized_text_answer),
        ).fetchall()
        return [
            {
                "attempt_id": row["attempt_id"],
                "student_id": row["student_id"],
                "text_answer": row["text_answer"],
            }
            for row in rows
        ]

    def list_attempt_ids_by_exam_and_status(
        self,
        exam_id: str,
        status: AttemptStatus,
        limit: int = 1000,
    ) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT id
            FROM attempts
            WHERE exam_id = ? AND status = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (exam_id, status.value, limit),
        ).fetchall()
        return [row["id"] for row in rows]
