"""Repository for managed student login IDs."""

from __future__ import annotations

import sqlite3
from typing import Protocol


class StudentRegistryRepository(Protocol):
    def exists(self, student_id: str) -> bool: ...

    def create_student(
        self,
        student_id: str,
        display_name: str | None,
        created_by: str,
        created_at: str,
    ) -> None: ...

    def list_students(self, limit: int = 300) -> list[dict]: ...


class SQLiteStudentRegistryRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def exists(self, student_id: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1
            FROM student_accounts
            WHERE student_id = ?
            LIMIT 1
            """,
            (student_id,),
        ).fetchone()
        return row is not None

    def create_student(
        self,
        student_id: str,
        display_name: str | None,
        created_by: str,
        created_at: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO student_accounts(
                student_id,
                display_name,
                created_by,
                created_at,
                status
            ) VALUES(?, ?, ?, ?, 'ACTIVE')
            """,
            (student_id, display_name, created_by, created_at),
        )

    def list_students(self, limit: int = 300) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT student_id, display_name, created_by, created_at, status
            FROM student_accounts
            ORDER BY created_at DESC, student_id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "student_id": row["student_id"],
                "display_name": row["display_name"],
                "created_by": row["created_by"],
                "created_at": row["created_at"],
                "status": row["status"],
            }
            for row in rows
        ]

