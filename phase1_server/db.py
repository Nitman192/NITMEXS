"""SQLite connection and hardening utilities for Phase A refactor."""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from phase1_server.schema_version import EXPECTED_SCHEMA_VERSION


@dataclass(frozen=True)
class SQLiteConfig:
    db_path: str
    busy_timeout_ms: int = 5000
    wal_autocheckpoint_pages: int = 1000
    synchronous: str = "NORMAL"
    foreign_keys: bool = True


class Database:
    """Lightweight connection manager with hardened SQLite pragmas."""

    def __init__(self, config: SQLiteConfig):
        self._config = config

    def initialize(self) -> None:
        Path(self._config.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.executescript(
                """


                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    exam_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 0,
                    submitted_at TEXT,
                    expires_at TEXT,
                    timer_frozen INTEGER NOT NULL DEFAULT 0,
                    timer_paused_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_attempts_candidate_id
                ON attempts(candidate_id);

                CREATE INDEX IF NOT EXISTS idx_attempts_exam_id
                ON attempts(exam_id);

                CREATE TABLE IF NOT EXISTS student_accounts (
                    student_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    password_hash TEXT NOT NULL DEFAULT '',
                    created_by TEXT NOT NULL,
                    owner_admin_id TEXT NOT NULL DEFAULT 'superadmin',
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE'
                );

                CREATE INDEX IF NOT EXISTS idx_student_accounts_created
                ON student_accounts(created_at DESC);

                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    key TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS questions (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    marks REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    owner_admin_id TEXT NOT NULL DEFAULT 'superadmin',
                    question_type TEXT NOT NULL DEFAULT 'mcq_single',
                    difficulty_level INTEGER,
                    discrimination_index REAL,
                    topic_tag TEXT,
                    cognitive_level TEXT,
                    word_target_min INTEGER,
                    word_target_max INTEGER,
                    word_hard_max INTEGER
                );

                CREATE INDEX IF NOT EXISTS idx_questions_topic_tag
                ON questions(topic_tag);

                CREATE INDEX IF NOT EXISTS idx_questions_cognitive_level
                ON questions(cognitive_level);

                CREATE TABLE IF NOT EXISTS options (
                    id TEXT PRIMARY KEY,
                    question_id TEXT NOT NULL,
                    option_text TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_options_question_id
                ON options(question_id);

                CREATE TABLE IF NOT EXISTS exams (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    negative_marking REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'DRAFT'
                        CHECK(status IN ('DRAFT', 'ACTIVE', 'CLOSED', 'ARCHIVED')),
                    published INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    owner_admin_id TEXT NOT NULL DEFAULT 'superadmin',
                    passing_percentage REAL NOT NULL DEFAULT 40,
                    reference_exam_id TEXT,
                    custom_rules_json TEXT
                );

                CREATE TABLE IF NOT EXISTS admin_accounts (
                    admin_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    role TEXT NOT NULL CHECK(role IN ('superadmin', 'examiner')),
                    access_key_hash TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS deployment_settings (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    deployment_profile TEXT NOT NULL,
                    branding_profile TEXT NOT NULL,
                    student_result_policy TEXT NOT NULL,
                    trusted_host_fingerprint TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS question_text_variants (
                    id TEXT PRIMARY KEY,
                    question_id TEXT NOT NULL,
                    answer_text TEXT NOT NULL,
                    normalized_answer_text TEXT NOT NULL,
                    decision TEXT NOT NULL CHECK(decision IN ('accepted', 'rejected')),
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_question_text_variants_question
                ON question_text_variants(question_id);

                CREATE INDEX IF NOT EXISTS idx_question_text_variants_norm
                ON question_text_variants(question_id, normalized_answer_text);

                CREATE TABLE IF NOT EXISTS exam_questions (
                    exam_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    PRIMARY KEY(exam_id, question_id),
                    FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE,
                    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_exam_questions_exam_id
                ON exam_questions(exam_id);

                CREATE INDEX IF NOT EXISTS idx_exam_questions_question_id
                ON exam_questions(question_id);

                CREATE TABLE IF NOT EXISTS attempt_question_snapshots (
                    attempt_id TEXT NOT NULL,
                    exam_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    order_index INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(attempt_id, question_id),
                    FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE,
                    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_attempt_snapshots_attempt_id
                ON attempt_question_snapshots(attempt_id);

                CREATE INDEX IF NOT EXISTS idx_attempt_snapshots_exam_id
                ON attempt_question_snapshots(exam_id);

                CREATE INDEX IF NOT EXISTS idx_attempt_snapshots_question_id
                ON attempt_question_snapshots(question_id);


                CREATE TABLE IF NOT EXISTS attempt_responses (
                    attempt_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    selected_option_id TEXT,
                    text_answer TEXT,
                    normalized_text_answer TEXT,
                    word_count INTEGER,
                    answered_at TEXT NOT NULL,
                    PRIMARY KEY(attempt_id, question_id),
                    FOREIGN KEY(attempt_id) REFERENCES attempts(id) ON DELETE CASCADE,
                    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE,
                    FOREIGN KEY(selected_option_id) REFERENCES options(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_attempt_responses_attempt_id
                ON attempt_responses(attempt_id);

                CREATE INDEX IF NOT EXISTS idx_attempt_responses_question_id
                ON attempt_responses(question_id);


                CREATE TABLE IF NOT EXISTS attempt_results (
                    attempt_id TEXT PRIMARY KEY,
                    total_score REAL NOT NULL,
                    total_possible_marks REAL NOT NULL,
                    percentage REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    graded_at TEXT NOT NULL,
                    FOREIGN KEY(attempt_id) REFERENCES attempts(id) ON DELETE CASCADE
                );


                CREATE UNIQUE INDEX IF NOT EXISTS idx_attempt_results_attempt_id_unique
                ON attempt_results(attempt_id);

                CREATE TABLE IF NOT EXISTS attempt_question_results (
                    attempt_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    question_type TEXT NOT NULL DEFAULT 'mcq_single',
                    selected_option_id TEXT,
                    correct_option_id TEXT,
                    text_answer TEXT,
                    matched_variant_id TEXT,
                    grading_state TEXT NOT NULL DEFAULT 'auto_incorrect',
                    marks_awarded REAL NOT NULL,
                    max_marks REAL NOT NULL,
                    is_correct INTEGER NOT NULL,
                    reviewed_by TEXT,
                    reviewed_at TEXT,
                    review_note TEXT,
                    PRIMARY KEY(attempt_id, question_id),
                    FOREIGN KEY(attempt_id) REFERENCES attempts(id) ON DELETE CASCADE,
                    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_attempt_question_results_attempt_id
                ON attempt_question_results(attempt_id);

                CREATE INDEX IF NOT EXISTS idx_attempt_question_results_question_id
                ON attempt_question_results(question_id);


                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    attempt_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    FOREIGN KEY(attempt_id) REFERENCES attempts(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_audit_logs_attempt_id
                ON audit_logs(attempt_id);

                CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type
                ON audit_logs(event_type);


                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    actor_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    version INTEGER
                );

                CREATE INDEX IF NOT EXISTS idx_audit_events_entity_id
                ON audit_events(entity_id);

                CREATE INDEX IF NOT EXISTS idx_audit_events_entity_created
                ON audit_events(entity_type, entity_id, created_at);

                CREATE TRIGGER IF NOT EXISTS trg_audit_events_no_update
                BEFORE UPDATE ON audit_events
                BEGIN
                    SELECT RAISE(ABORT, 'audit_events is immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_audit_events_no_delete
                BEFORE DELETE ON audit_events
                BEGIN
                    SELECT RAISE(ABORT, 'audit_events is immutable');
                END;


                CREATE TABLE IF NOT EXISTS system_metrics (
                    metric_name TEXT NOT NULL,
                    metric_key TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    total_value REAL NOT NULL DEFAULT 0,
                    max_value REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(metric_name, metric_key)
                );

                CREATE INDEX IF NOT EXISTS idx_system_metrics_name
                ON system_metrics(metric_name);



                CREATE TABLE IF NOT EXISTS item_statistics (
                    exam_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    attempts_count INTEGER NOT NULL DEFAULT 0,
                    correct_count INTEGER NOT NULL DEFAULT 0,
                    total_marks_awarded REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY(exam_id, question_id),
                    FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE,
                    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_item_statistics_exam_id
                ON item_statistics(exam_id);

                CREATE INDEX IF NOT EXISTS idx_item_statistics_question_id
                ON item_statistics(question_id);

                CREATE TABLE IF NOT EXISTS question_recalibration_runs (
                    id TEXT PRIMARY KEY,
                    exam_id TEXT NOT NULL,
                    mode TEXT NOT NULL
                        CHECK(mode IN ('preview', 'apply', 'rollback')),
                    min_attempts INTEGER,
                    total_questions INTEGER NOT NULL,
                    eligible_questions INTEGER NOT NULL,
                    updated_questions INTEGER NOT NULL,
                    skipped_questions INTEGER NOT NULL,
                    triggered_by TEXT NOT NULL,
                    source_run_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE,
                    FOREIGN KEY(source_run_id) REFERENCES question_recalibration_runs(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_question_recalibration_runs_exam_created
                ON question_recalibration_runs(exam_id, created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_question_recalibration_runs_source
                ON question_recalibration_runs(source_run_id);

                CREATE TABLE IF NOT EXISTS question_recalibration_items (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    total_attempts INTEGER NOT NULL DEFAULT 0,
                    observed_difficulty_index REAL,
                    previous_difficulty TEXT,
                    previous_difficulty_level INTEGER,
                    previous_discrimination_index REAL,
                    suggested_difficulty TEXT,
                    suggested_difficulty_level INTEGER,
                    suggested_discrimination_index REAL,
                    applied INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES question_recalibration_runs(id) ON DELETE CASCADE,
                    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_question_recalibration_items_run
                ON question_recalibration_items(run_id);

                CREATE INDEX IF NOT EXISTS idx_question_recalibration_items_question
                ON question_recalibration_items(question_id);

                CREATE TABLE IF NOT EXISTS proctor_alerts (
                    id TEXT PRIMARY KEY,
                    attempt_id TEXT NOT NULL,
                    exam_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    indicator_code TEXT NOT NULL,
                    indicator_payload_json TEXT NOT NULL,
                    status TEXT NOT NULL
                        CHECK(status IN ('open', 'acknowledged', 'resolved')),
                    detection_count INTEGER NOT NULL DEFAULT 1,
                    first_detected_at TEXT NOT NULL,
                    last_detected_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    acknowledged_at TEXT,
                    acknowledged_by TEXT,
                    resolved_at TEXT,
                    resolved_by TEXT,
                    resolution_note TEXT,
                    FOREIGN KEY(attempt_id) REFERENCES attempts(id) ON DELETE CASCADE,
                    FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_proctor_alerts_exam_status_created
                ON proctor_alerts(exam_id, status, created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_proctor_alerts_status_created
                ON proctor_alerts(status, created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_proctor_alerts_attempt_status
                ON proctor_alerts(attempt_id, status);

                CREATE UNIQUE INDEX IF NOT EXISTS idx_proctor_alerts_open_unique
                ON proctor_alerts(attempt_id, indicator_code)
                WHERE status IN ('open', 'acknowledged');

                CREATE TABLE IF NOT EXISTS exam_audit_logs (
                    id TEXT PRIMARY KEY,
                    exam_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_exam_audit_logs_exam_id
                ON exam_audit_logs(exam_id);

                """
            )


            attempt_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(attempts)").fetchall()
            }
            if "version" not in attempt_columns:
                conn.execute(
                    "ALTER TABLE attempts ADD COLUMN version INTEGER NOT NULL DEFAULT 0"
                )
            if "timer_frozen" not in attempt_columns:
                conn.execute(
                    "ALTER TABLE attempts ADD COLUMN timer_frozen INTEGER NOT NULL DEFAULT 0"
                )
            if "timer_paused_at" not in attempt_columns:
                conn.execute("ALTER TABLE attempts ADD COLUMN timer_paused_at TEXT")

            exam_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(exams)").fetchall()
            }
            if "status" not in exam_columns:
                conn.execute(
                    "ALTER TABLE exams ADD COLUMN status TEXT NOT NULL DEFAULT 'DRAFT'"
                )
                conn.execute(
                    "UPDATE exams SET status = CASE WHEN published = 1 THEN 'ACTIVE' ELSE 'DRAFT' END"
                )

            question_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(questions)").fetchall()
            }
            if "question_type" not in question_columns:
                conn.execute(
                    "ALTER TABLE questions ADD COLUMN question_type TEXT NOT NULL DEFAULT 'mcq_single'"
                )
            if "owner_admin_id" not in question_columns:
                conn.execute(
                    "ALTER TABLE questions ADD COLUMN owner_admin_id TEXT NOT NULL DEFAULT 'superadmin'"
                )
            if "difficulty_level" not in question_columns:
                conn.execute("ALTER TABLE questions ADD COLUMN difficulty_level INTEGER")
            if "discrimination_index" not in question_columns:
                conn.execute("ALTER TABLE questions ADD COLUMN discrimination_index REAL")
            if "topic_tag" not in question_columns:
                conn.execute("ALTER TABLE questions ADD COLUMN topic_tag TEXT")
                conn.execute(
                    "UPDATE questions SET topic_tag = topic WHERE topic_tag IS NULL"
                )
            if "cognitive_level" not in question_columns:
                conn.execute("ALTER TABLE questions ADD COLUMN cognitive_level TEXT")
            if "word_target_min" not in question_columns:
                conn.execute("ALTER TABLE questions ADD COLUMN word_target_min INTEGER")
            if "word_target_max" not in question_columns:
                conn.execute("ALTER TABLE questions ADD COLUMN word_target_max INTEGER")
            if "word_hard_max" not in question_columns:
                conn.execute("ALTER TABLE questions ADD COLUMN word_hard_max INTEGER")
            conn.execute(
                "UPDATE questions SET question_type = 'mcq_single' WHERE question_type IS NULL OR TRIM(question_type) = ''"
            )

            if "reference_exam_id" not in exam_columns:
                conn.execute("ALTER TABLE exams ADD COLUMN reference_exam_id TEXT")
            if "owner_admin_id" not in exam_columns:
                conn.execute(
                    "ALTER TABLE exams ADD COLUMN owner_admin_id TEXT NOT NULL DEFAULT 'superadmin'"
                )
            if "custom_rules_json" not in exam_columns:
                conn.execute("ALTER TABLE exams ADD COLUMN custom_rules_json TEXT")

            conn.execute(
                """
                INSERT OR IGNORE INTO deployment_settings(
                    id, deployment_profile, branding_profile, student_result_policy, trusted_host_fingerprint, created_at, updated_at
                ) VALUES(1, 'army_basic', 'indian_army_education', 'no_student_result', NULL, datetime('now'), datetime('now'))
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS question_text_variants (
                    id TEXT PRIMARY KEY,
                    question_id TEXT NOT NULL,
                    answer_text TEXT NOT NULL,
                    normalized_answer_text TEXT NOT NULL,
                    decision TEXT NOT NULL CHECK(decision IN ('accepted', 'rejected')),
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_question_text_variants_question
                ON question_text_variants(question_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_question_text_variants_norm
                ON question_text_variants(question_id, normalized_answer_text)
                """
            )

            attempt_response_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(attempt_responses)").fetchall()
            }
            if attempt_response_columns and (
                "text_answer" not in attempt_response_columns
                or "normalized_text_answer" not in attempt_response_columns
                or "word_count" not in attempt_response_columns
            ):
                conn.execute("ALTER TABLE attempt_responses RENAME TO attempt_responses_legacy")
                conn.execute(
                    """
                    CREATE TABLE attempt_responses (
                        attempt_id TEXT NOT NULL,
                        question_id TEXT NOT NULL,
                        selected_option_id TEXT,
                        text_answer TEXT,
                        normalized_text_answer TEXT,
                        word_count INTEGER,
                        answered_at TEXT NOT NULL,
                        PRIMARY KEY(attempt_id, question_id),
                        FOREIGN KEY(attempt_id) REFERENCES attempts(id) ON DELETE CASCADE,
                        FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE,
                        FOREIGN KEY(selected_option_id) REFERENCES options(id) ON DELETE CASCADE
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO attempt_responses(
                        attempt_id, question_id, selected_option_id, answered_at
                    )
                    SELECT attempt_id, question_id, selected_option_id, answered_at
                    FROM attempt_responses_legacy
                    """
                )
                conn.execute("DROP TABLE attempt_responses_legacy")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_attempt_responses_attempt_id ON attempt_responses(attempt_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_attempt_responses_question_id ON attempt_responses(question_id)"
                )

            conn.execute("DROP TRIGGER IF EXISTS trg_attempt_results_no_update")
            conn.execute("DROP TRIGGER IF EXISTS trg_attempt_results_no_delete")
            conn.execute("DROP TRIGGER IF EXISTS trg_attempt_question_results_no_update")
            conn.execute("DROP TRIGGER IF EXISTS trg_attempt_question_results_no_delete")

            question_result_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(attempt_question_results)").fetchall()
            }
            if question_result_columns and (
                "question_type" not in question_result_columns
                or "text_answer" not in question_result_columns
                or "matched_variant_id" not in question_result_columns
                or "grading_state" not in question_result_columns
                or "reviewed_by" not in question_result_columns
                or "reviewed_at" not in question_result_columns
                or "review_note" not in question_result_columns
            ):
                conn.execute(
                    "ALTER TABLE attempt_question_results RENAME TO attempt_question_results_legacy"
                )
                conn.execute(
                    """
                    CREATE TABLE attempt_question_results (
                        attempt_id TEXT NOT NULL,
                        question_id TEXT NOT NULL,
                        question_type TEXT NOT NULL DEFAULT 'mcq_single',
                        selected_option_id TEXT,
                        correct_option_id TEXT,
                        text_answer TEXT,
                        matched_variant_id TEXT,
                        grading_state TEXT NOT NULL DEFAULT 'auto_incorrect',
                        marks_awarded REAL NOT NULL,
                        max_marks REAL NOT NULL,
                        is_correct INTEGER NOT NULL,
                        reviewed_by TEXT,
                        reviewed_at TEXT,
                        review_note TEXT,
                        PRIMARY KEY(attempt_id, question_id),
                        FOREIGN KEY(attempt_id) REFERENCES attempts(id) ON DELETE CASCADE,
                        FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT INTO attempt_question_results(
                        attempt_id, question_id, question_type, selected_option_id, correct_option_id,
                        grading_state, marks_awarded, max_marks, is_correct
                    )
                    SELECT
                        legacy.attempt_id,
                        legacy.question_id,
                        COALESCE(q.question_type, 'mcq_single'),
                        legacy.selected_option_id,
                        legacy.correct_option_id,
                        CASE WHEN legacy.is_correct = 1 THEN 'auto_correct' ELSE 'auto_incorrect' END,
                        legacy.marks_awarded,
                        legacy.max_marks,
                        legacy.is_correct
                    FROM attempt_question_results_legacy legacy
                    LEFT JOIN questions q ON q.id = legacy.question_id
                    """
                )
                conn.execute("DROP TABLE attempt_question_results_legacy")
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_attempt_question_results_attempt_id ON attempt_question_results(attempt_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_attempt_question_results_question_id ON attempt_question_results(question_id)"
                )

            recalibration_run_columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(question_recalibration_runs)"
                ).fetchall()
            }
            if recalibration_run_columns and "source_run_id" not in recalibration_run_columns:
                conn.execute(
                    "ALTER TABLE question_recalibration_runs ADD COLUMN source_run_id TEXT"
                )

            proctor_alert_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(proctor_alerts)").fetchall()
            }
            if proctor_alert_columns and "detection_count" not in proctor_alert_columns:
                conn.execute(
                    "ALTER TABLE proctor_alerts ADD COLUMN detection_count INTEGER NOT NULL DEFAULT 1"
                )
            if proctor_alert_columns and "resolution_note" not in proctor_alert_columns:
                conn.execute("ALTER TABLE proctor_alerts ADD COLUMN resolution_note TEXT")

            student_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(student_accounts)").fetchall()
            }
            if student_columns and "status" not in student_columns:
                conn.execute(
                    "ALTER TABLE student_accounts ADD COLUMN status TEXT NOT NULL DEFAULT 'ACTIVE'"
                )
            if student_columns and "password_hash" not in student_columns:
                conn.execute(
                    "ALTER TABLE student_accounts ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''"
                )
                conn.execute(
                    "UPDATE student_accounts SET password_hash = ? WHERE COALESCE(password_hash, '') = ''",
                    (self._legacy_student_password_hash(),),
                )
            if student_columns and "owner_admin_id" not in student_columns:
                conn.execute(
                    "ALTER TABLE student_accounts ADD COLUMN owner_admin_id TEXT NOT NULL DEFAULT 'superadmin'"
                )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_accounts (
                    admin_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    role TEXT NOT NULL CHECK(role IN ('superadmin', 'examiner')),
                    access_key_hash TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO admin_accounts(
                    admin_id, display_name, role, access_key_hash, status, created_by, created_at
                ) VALUES(?, ?, 'superadmin', ?, 'ACTIVE', 'system', datetime('now'))
                """,
                ("superadmin", "Super Admin", self._superadmin_password_hash()),
            )

            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES(?, datetime('now'))",
                (EXPECTED_SCHEMA_VERSION,),
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(
            self._config.db_path,
            timeout=self._config.busy_timeout_ms / 1000,
        )
        conn.row_factory = sqlite3.Row
        self._apply_pragmas(conn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def close(self) -> None:
        """Database manager shutdown hook (no persistent connection to close)."""

    def get_schema_version(self) -> int | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
            ).fetchone()
            return None if row is None else int(row["version"])

    def ensure_expected_schema_version(self, expected_version: int) -> None:
        actual = self.get_schema_version()
        if actual != expected_version:
            raise RuntimeError(
                f"Schema version mismatch: expected {expected_version}, got {actual}"
            )

    def _apply_pragmas(self, conn: sqlite3.Connection) -> None:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(f"PRAGMA busy_timeout={self._config.busy_timeout_ms};")
        conn.execute(
            f"PRAGMA wal_autocheckpoint={self._config.wal_autocheckpoint_pages};"
        )
        conn.execute(f"PRAGMA synchronous={self._config.synchronous};")
        conn.execute(f"PRAGMA foreign_keys={1 if self._config.foreign_keys else 0};")

    @staticmethod
    def _superadmin_password_hash() -> str:
        return hashlib.sha256("superadmin:nitmexs-admin".encode("utf-8")).hexdigest()

    @staticmethod
    def _legacy_student_password_hash() -> str:
        return hashlib.sha256("legacy:legacy".encode("utf-8")).hexdigest()


def get_connection_dependency(db: Database):
    """FastAPI-friendly generator dependency for per-request connection scope."""

    def _dependency():
        with db.connection() as conn:
            yield conn

    return _dependency
