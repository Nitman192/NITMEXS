"""Unit-of-work helper for repository extraction pattern."""

from __future__ import annotations

from contextlib import AbstractContextManager

from phase1_server.db import Database
from phase1_server.repositories.attempt_repository import SQLiteAttemptRepository
from phase1_server.repositories.audit_event_repository import SQLiteAuditEventRepository
from phase1_server.repositories.exam_repository import SQLiteExamRepository
from phase1_server.repositories.metrics_repository import SQLiteMetricsRepository
from phase1_server.repositories.question_repository import SQLiteQuestionRepository


class UnitOfWork(AbstractContextManager):
    def __init__(self, db: Database):
        self._db = db
        self._ctx = None
        self.conn = None
        self.attempts: SQLiteAttemptRepository | None = None
        self.questions: SQLiteQuestionRepository | None = None
        self.exams: SQLiteExamRepository | None = None
        self.audit_events: SQLiteAuditEventRepository | None = None
        self.metrics: SQLiteMetricsRepository | None = None

    def __enter__(self):
        self._ctx = self._db.connection()
        self.conn = self._ctx.__enter__()
        self.attempts = SQLiteAttemptRepository(self.conn)
        self.questions = SQLiteQuestionRepository(self.conn)
        self.exams = SQLiteExamRepository(self.conn)
        self.audit_events = SQLiteAuditEventRepository(self.conn)
        self.metrics = SQLiteMetricsRepository(self.conn)
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._ctx.__exit__(exc_type, exc, tb)
