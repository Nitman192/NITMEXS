"""Operational durability simulation utilities for backup/restore integrity."""

from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

from phase1_server.db import Database, SQLiteConfig
from phase1_server.services.exam_service import ExamCreatePayload, ExamService
from phase1_server.services.question_service import QuestionCreatePayload, QuestionService
from phase1_server.uow import UnitOfWork


def seed_exam(db_path: str) -> str:
    db = Database(SQLiteConfig(db_path=db_path))
    db.initialize()
    with UnitOfWork(db) as uow:
        q_service = QuestionService(uow.questions)
        qids = []
        for i in range(3):
            question = q_service.create_question(
                QuestionCreatePayload(
                    text=f"Durability Q{i}",
                    topic="ops",
                    difficulty="easy",
                    marks=1,
                    options=[("A", True), ("B", False)],
                )
            )
            qids.append(question.id)

        exam_service = ExamService(uow.exams, uow.questions)
        exam = exam_service.create_exam(
            ExamCreatePayload(name="Durability Exam", duration_minutes=20, negative_marking=0)
        )
        exam_service.add_questions(exam.id, qids)
        exam_service.publish_exam(exam.id)
        return exam.id


def wait_server(base_url: str, timeout_s: float = 15.0) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            r = httpx.get(f"{base_url}/system/version", timeout=2.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.3)
    raise RuntimeError("Server did not become ready")


def sqlite_integrity_ok(path: str) -> bool:
    conn = sqlite3.connect(path)
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        return row is not None and row[0] == "ok"
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="NITMEXS durability simulation")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--students", type=int, default=8)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "durability.db")
        exam_id = seed_exam(db_path)

        env = os.environ.copy()
        env["NITMEXS_DB_PATH"] = db_path
        env["NITMEXS_HOST"] = "127.0.0.1"
        env["NITMEXS_PORT"] = "8000"

        server = subprocess.Popen(
            [sys.executable, "-m", "phase1_server.server_entry", "--mode", "foreground"],
            env=env,
        )

        try:
            wait_server(args.base_url)

            # Active attempts while backup triggers.
            for i in range(args.students):
                httpx.post(
                    f"{args.base_url}/student/exams/{exam_id}/start",
                    headers={"x-student-id": f"durability-{i}"},
                    timeout=10.0,
                )

            backup_proc = subprocess.run(
                [sys.executable, "-m", "phase1_server.server_entry", "--backup"],
                env=env,
                check=False,
            )
            if backup_proc.returncode != 0:
                raise RuntimeError("Backup mode failed")

            backups = sorted((Path(tmp_dir) / "backups").glob("*.db"))
            if not backups:
                raise RuntimeError("Backup file not produced")

            backup_path = str(backups[-1])
            if not sqlite_integrity_ok(backup_path):
                raise RuntimeError("Backup integrity check failed")

            restore_proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "phase1_server.server_entry",
                    "--restore",
                    backup_path,
                ],
                env=env,
                check=False,
            )
            if restore_proc.returncode != 0:
                raise RuntimeError("Restore mode failed")

            if not sqlite_integrity_ok(db_path):
                raise RuntimeError("Restored DB integrity check failed")

            print("Durability simulation completed successfully")
            print(f"backup_path={backup_path}")
            return 0
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
