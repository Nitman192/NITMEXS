"""Repository for admin and examiner account persistence."""

from __future__ import annotations

import sqlite3
from typing import Protocol

from phase1_server.models import AdminAccount, AdminRole


class AdminAccountRepository(Protocol):
    def get_account(self, admin_id: str) -> AdminAccount | None: ...

    def list_accounts(self) -> list[AdminAccount]: ...

    def create_account(self, account: AdminAccount) -> None: ...


class SQLiteAdminAccountRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_account(self, admin_id: str) -> AdminAccount | None:
        row = self._conn.execute(
            """
            SELECT admin_id, display_name, role, access_key_hash, status, created_by, created_at
            FROM admin_accounts
            WHERE admin_id = ?
            LIMIT 1
            """,
            (admin_id,),
        ).fetchone()
        return None if row is None else self._account_from_row(row)

    def list_accounts(self) -> list[AdminAccount]:
        rows = self._conn.execute(
            """
            SELECT admin_id, display_name, role, access_key_hash, status, created_by, created_at
            FROM admin_accounts
            ORDER BY created_at ASC, admin_id ASC
            """
        ).fetchall()
        return [self._account_from_row(row) for row in rows]

    def create_account(self, account: AdminAccount) -> None:
        self._conn.execute(
            """
            INSERT INTO admin_accounts(
                admin_id, display_name, role, access_key_hash, status, created_by, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account.admin_id,
                account.display_name,
                account.role.value,
                account.access_key_hash,
                account.status,
                account.created_by,
                account.created_at,
            ),
        )

    @staticmethod
    def _account_from_row(row: sqlite3.Row) -> AdminAccount:
        return AdminAccount(
            admin_id=row["admin_id"],
            display_name=row["display_name"],
            role=AdminRole(row["role"]),
            access_key_hash=row["access_key_hash"],
            status=row["status"],
            created_by=row["created_by"],
            created_at=row["created_at"],
        )
