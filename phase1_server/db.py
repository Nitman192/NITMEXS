"""SQLite connection and hardening utilities for Phase A refactor."""

from __future__ import annotations

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
                    expires_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_attempts_candidate_id
                ON attempts(candidate_id);

                CREATE INDEX IF NOT EXISTS idx_attempts_exam_id
                ON attempts(exam_id);

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
                    difficulty_level INTEGER,
                    discrimination_index REAL,
                    topic_tag TEXT,
                    cognitive_level TEXT
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
                    passing_percentage REAL NOT NULL DEFAULT 40
                );

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
                    selected_option_id TEXT NOT NULL,
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
                    selected_option_id TEXT,
                    correct_option_id TEXT NOT NULL,
                    marks_awarded REAL NOT NULL,
                    max_marks REAL NOT NULL,
                    is_correct INTEGER NOT NULL,
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

                CREATE TRIGGER IF NOT EXISTS trg_attempt_results_no_update
                BEFORE UPDATE ON attempt_results
                BEGIN
                    SELECT RAISE(ABORT, 'attempt_results is immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_attempt_results_no_delete
                BEFORE DELETE ON attempt_results
                BEGIN
                    SELECT RAISE(ABORT, 'attempt_results is immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_attempt_question_results_no_update
                BEFORE UPDATE ON attempt_question_results
                BEGIN
                    SELECT RAISE(ABORT, 'attempt_question_results is immutable');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_attempt_question_results_no_delete
                BEFORE DELETE ON attempt_question_results
                BEGIN
                    SELECT RAISE(ABORT, 'attempt_question_results is immutable');
                END;
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


def get_connection_dependency(db: Database):
    """FastAPI-friendly generator dependency for per-request connection scope."""

    def _dependency():
        with db.connection() as conn:
            yield conn

    return _dependency
