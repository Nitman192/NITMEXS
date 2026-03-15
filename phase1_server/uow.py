"""Unit-of-work helper for repository extraction pattern."""

from __future__ import annotations

from contextlib import AbstractContextManager

from phase1_server.db import Database
from phase1_server.repositories.analytics_repository import SQLiteAnalyticsRepository
from phase1_server.repositories.admin_account_repository import SQLiteAdminAccountRepository
from phase1_server.repositories.attempt_repository import SQLiteAttemptRepository
from phase1_server.repositories.audit_event_repository import SQLiteAuditEventRepository
from phase1_server.repositories.deployment_repository import (
    SQLiteDeploymentSettingsRepository,
)
from phase1_server.repositories.exam_repository import SQLiteExamRepository
from phase1_server.repositories.metrics_repository import SQLiteMetricsRepository
from phase1_server.repositories.proctor_alert_repository import (
    SQLiteProctorAlertRepository,
)
from phase1_server.repositories.question_recalibration_repository import (
    SQLiteQuestionRecalibrationRepository,
)
from phase1_server.repositories.question_repository import SQLiteQuestionRepository
from phase1_server.repositories.student_registry_repository import (
    SQLiteStudentRegistryRepository,
)


class UnitOfWork(AbstractContextManager):
    def __init__(self, db: Database):
        self._db = db
        self._ctx = None
        self.conn = None
        self.attempts: SQLiteAttemptRepository | None = None
        self.questions: SQLiteQuestionRepository | None = None
        self.exams: SQLiteExamRepository | None = None
        self.deployment_settings: SQLiteDeploymentSettingsRepository | None = None
        self.audit_events: SQLiteAuditEventRepository | None = None
        self.metrics: SQLiteMetricsRepository | None = None
        self.analytics: SQLiteAnalyticsRepository | None = None
        self.recalibration_runs: SQLiteQuestionRecalibrationRepository | None = None
        self.proctor_alerts: SQLiteProctorAlertRepository | None = None
        self.student_accounts: SQLiteStudentRegistryRepository | None = None
        self.admin_accounts: SQLiteAdminAccountRepository | None = None

    def __enter__(self):
        self._ctx = self._db.connection()
        self.conn = self._ctx.__enter__()
        self.attempts = SQLiteAttemptRepository(self.conn)
        self.questions = SQLiteQuestionRepository(self.conn)
        self.exams = SQLiteExamRepository(self.conn)
        self.deployment_settings = SQLiteDeploymentSettingsRepository(self.conn)
        self.audit_events = SQLiteAuditEventRepository(self.conn)
        self.metrics = SQLiteMetricsRepository(self.conn)
        self.analytics = SQLiteAnalyticsRepository(self.conn)
        self.recalibration_runs = SQLiteQuestionRecalibrationRepository(self.conn)
        self.proctor_alerts = SQLiteProctorAlertRepository(self.conn)
        self.student_accounts = SQLiteStudentRegistryRepository(self.conn)
        self.admin_accounts = SQLiteAdminAccountRepository(self.conn)
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._ctx.__exit__(exc_type, exc, tb)
