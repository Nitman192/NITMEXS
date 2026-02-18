"""SQLite connection and hardening utilities for Phase A refactor."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


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
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    exam_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    submitted_at TEXT
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
                    created_at TEXT NOT NULL
                );

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
                    published INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
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
                """
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
