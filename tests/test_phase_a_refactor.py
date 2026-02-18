import tempfile
import unittest

from phase1_server.db import Database, SQLiteConfig
from phase1_server.models import Attempt, AttemptStatus, utc_now_iso
from phase1_server.services.attempt_state_service import (
    AttemptStateService,
    InvalidAttemptTransitionError,
)
from phase1_server.uow import UnitOfWork


class PhaseARefactorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db")
        self.db = Database(SQLiteConfig(db_path=self.tmp.name))
        self.db.initialize()

    def tearDown(self):
        self.tmp.close()

    def test_pragmas_are_applied(self):
        with self.db.connection() as conn:
            mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
            timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
        self.assertEqual(mode.lower(), "wal")
        self.assertEqual(timeout, 5000)

    def test_attempt_transition_valid(self):
        now = utc_now_iso()
        with UnitOfWork(self.db) as uow:
            uow.attempts.create(
                Attempt(
                    id="a1",
                    candidate_id="c1",
                    exam_id="e1",
                    status=AttemptStatus.CREATED,
                    created_at=now,
                    updated_at=now,
                )
            )
            service = AttemptStateService(uow.attempts)
            result = service.transition("a1", AttemptStatus.ACTIVE)

        self.assertEqual(result.from_status, AttemptStatus.CREATED)
        self.assertEqual(result.to_status, AttemptStatus.ACTIVE)

    def test_attempt_transition_invalid(self):
        now = utc_now_iso()
        with UnitOfWork(self.db) as uow:
            uow.attempts.create(
                Attempt(
                    id="a2",
                    candidate_id="c1",
                    exam_id="e1",
                    status=AttemptStatus.CREATED,
                    created_at=now,
                    updated_at=now,
                )
            )
            service = AttemptStateService(uow.attempts)
            with self.assertRaises(InvalidAttemptTransitionError):
                service.transition("a2", AttemptStatus.GRADED)


if __name__ == "__main__":
    unittest.main()
