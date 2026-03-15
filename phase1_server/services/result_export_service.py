"""Admin-side result publication, preview, and export helpers."""

from __future__ import annotations

import csv
import hashlib
import io
import textwrap
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from html import escape

from phase1_server.models import ResultArtifact
from phase1_server.repositories.attempt_repository import AttemptRepository
from phase1_server.repositories.exam_repository import ExamRepository
from phase1_server.repositories.question_repository import QuestionRepository
from phase1_server.repositories.result_artifact_repository import ResultArtifactRepository
from phase1_server.repositories.student_registry_repository import StudentRegistryRepository
from phase1_server.services.audit_service import AuditService
from phase1_server.services.analytics_service import AnalyticsService
from phase1_server.services.exam_service import ExamNotFoundError
from phase1_server.services.grading_service import GradingEngine, ResultNotReadyError


class ResultExportError(ValueError):
    pass


class ResultPublicationError(ResultExportError):
    pass


class ResultArtifactNotReadyError(ResultExportError):
    pass


class ResultExportService:
    def __init__(
        self,
        attempt_repo: AttemptRepository,
        exam_repo: ExamRepository,
        question_repo: QuestionRepository,
        student_repo: StudentRegistryRepository,
        artifact_repo: ResultArtifactRepository,
        audit_service: AuditService | None = None,
        analytics_service: AnalyticsService | None = None,
    ):
        self._attempt_repo = attempt_repo
        self._exam_repo = exam_repo
        self._question_repo = question_repo
        self._student_repo = student_repo
        self._artifact_repo = artifact_repo
        self._audit_service = audit_service
        self._analytics_service = analytics_service

    def list_exam_results(self, exam_id: str) -> dict:
        exam = self._get_exam(exam_id)
        rows = self._attempt_repo.list_exam_results(exam_id)
        pending_reviews = self._attempt_repo.count_pending_reviews_by_exam(exam_id)
        return {
            "exam_id": exam.id,
            "exam_name": exam.name,
            "results_published": exam.results_published,
            "results_published_at": exam.results_published_at,
            "results_published_by": exam.results_published_by,
            "pending_review_count": pending_reviews,
            "ready_result_count": sum(1 for row in rows if row.get("percentage") is not None),
            "candidates": rows,
        }

    def publish_exam_results(self, exam_id: str, actor_id: str, actor_role: str = "admin") -> dict:
        exam = self._get_exam(exam_id)
        pending_reviews = self._attempt_repo.count_pending_reviews_by_exam(exam_id)
        if pending_reviews > 0:
            raise ResultPublicationError("Cannot publish results while review items are pending")
        ready_results = self._attempt_repo.count_ready_results_by_exam(exam_id)
        if ready_results <= 0:
            raise ResultPublicationError("No finalized reviewed results are available for publication")

        published_at = self._now_iso()
        self._exam_repo.set_result_publication(
            exam_id,
            published=True,
            published_at=published_at,
            published_by=actor_id,
        )
        self._log_event(
            entity_type="exam",
            entity_id=exam_id,
            actor_type=actor_role,
            actor_id=actor_id,
            event_type="RESULTS_PUBLISHED",
            payload={"ready_result_count": ready_results},
            created_at=published_at,
        )
        updated = self._get_exam(exam_id)
        return {
            "exam_id": updated.id,
            "results_published": updated.results_published,
            "results_published_at": updated.results_published_at,
            "results_published_by": updated.results_published_by,
            "ready_result_count": ready_results,
        }

    def unpublish_exam_results(self, exam_id: str, actor_id: str, actor_role: str = "admin") -> dict:
        self._get_exam(exam_id)
        unpublished_at = self._now_iso()
        self._exam_repo.set_result_publication(
            exam_id,
            published=False,
            published_at=None,
            published_by=None,
        )
        self._log_event(
            entity_type="exam",
            entity_id=exam_id,
            actor_type=actor_role,
            actor_id=actor_id,
            event_type="RESULTS_UNPUBLISHED",
            payload={},
            created_at=unpublished_at,
        )
        updated = self._get_exam(exam_id)
        return {
            "exam_id": updated.id,
            "results_published": updated.results_published,
        }

    def render_result_preview_html(self, attempt_id: str, actor_id: str) -> str:
        sheet = self._build_result_sheet(attempt_id)
        html = self._render_result_html(sheet)
        self._register_artifact(
            artifact_type="result_preview_html",
            entity_type="exam",
            entity_id=sheet["exam_id"],
            created_by=actor_id,
            file_name=f"result_preview_{attempt_id}.html",
            content_type="text/html",
            raw_bytes=html.encode("utf-8"),
            reference_code=sheet["reference_code"],
        )
        return html

    def export_result_pdf(self, attempt_id: str, actor_id: str) -> bytes:
        sheet = self._build_result_sheet(attempt_id)
        if not sheet["results_published"]:
            raise ResultArtifactNotReadyError("Publish exam results before downloading final PDF sheets")
        pdf = self._render_result_pdf(sheet)
        self._register_artifact(
            artifact_type="result_sheet_pdf",
            entity_type="exam",
            entity_id=sheet["exam_id"],
            created_by=actor_id,
            file_name=f"result_sheet_{attempt_id}.pdf",
            content_type="application/pdf",
            raw_bytes=pdf,
            reference_code=sheet["reference_code"],
        )
        return pdf

    def export_exam_results_csv(self, exam_id: str, actor_id: str) -> str:
        exam = self._get_exam(exam_id)
        if not exam.results_published:
            raise ResultArtifactNotReadyError("Publish exam results before exporting final CSV")
        rows = self._attempt_repo.list_exam_results(exam_id)
        ready_rows = [row for row in rows if row.get("percentage") is not None and row.get("pending_review_count", 0) == 0]
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "exam_id",
                "exam_name",
                "attempt_id",
                "student_id",
                "display_name",
                "total_score",
                "total_possible_marks",
                "percentage",
                "passed",
                "graded_at",
                "published_at",
                "published_by",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in ready_rows:
            writer.writerow(
                {
                    "exam_id": exam.id,
                    "exam_name": exam.name,
                    "attempt_id": row["attempt_id"],
                    "student_id": row["student_id"],
                    "display_name": row["display_name"],
                    "total_score": row["total_score"],
                    "total_possible_marks": row["total_possible_marks"],
                    "percentage": row["percentage"],
                    "passed": row["passed"],
                    "graded_at": row["graded_at"],
                    "published_at": exam.results_published_at,
                    "published_by": exam.results_published_by,
                }
            )
        content = output.getvalue()
        self._register_artifact(
            artifact_type="exam_results_csv",
            entity_type="exam",
            entity_id=exam_id,
            created_by=actor_id,
            file_name=f"exam_results_{exam_id}.csv",
            content_type="text/csv",
            raw_bytes=content.encode("utf-8"),
            reference_code=self._exam_reference_code(exam.id),
        )
        return content

    def export_pending_review_csv(self, exam_id: str, actor_id: str) -> str:
        exam = self._get_exam(exam_id)
        fib_rows = self._attempt_repo.list_fib_review_queue(exam_id)
        subjective_rows = self._attempt_repo.list_subjective_review_queue(exam_id)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "exam_id",
                "exam_name",
                "queue_type",
                "question_id",
                "student_id",
                "normalized_text_answer",
                "sample_answer",
                "attempt_id",
                "word_count",
                "submission_count",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in fib_rows:
            writer.writerow(
                {
                    "exam_id": exam.id,
                    "exam_name": exam.name,
                    "queue_type": "fib_review",
                    "question_id": row["question_id"],
                    "student_id": ",".join(row.get("student_ids", [])),
                    "normalized_text_answer": row["normalized_text_answer"],
                    "sample_answer": row["sample_answer"],
                    "attempt_id": ",".join(row.get("attempt_ids", [])),
                    "word_count": "",
                    "submission_count": row["submission_count"],
                }
            )
        for row in subjective_rows:
            writer.writerow(
                {
                    "exam_id": exam.id,
                    "exam_name": exam.name,
                    "queue_type": "subjective_review",
                    "question_id": row["question_id"],
                    "student_id": row["student_id"],
                    "normalized_text_answer": "",
                    "sample_answer": row["text_answer"],
                    "attempt_id": row["attempt_id"],
                    "word_count": row["word_count"],
                    "submission_count": 1,
                }
            )
        content = output.getvalue()
        self._register_artifact(
            artifact_type="pending_review_csv",
            entity_type="exam",
            entity_id=exam_id,
            created_by=actor_id,
            file_name=f"pending_review_{exam_id}.csv",
            content_type="text/csv",
            raw_bytes=content.encode("utf-8"),
            reference_code=self._exam_reference_code(exam.id),
        )
        return content

    def list_artifacts(self, exam_id: str | None = None, limit: int = 25) -> list[dict]:
        rows = self._artifact_repo.list_recent(
            entity_type=None if exam_id is None else "exam",
            entity_id=exam_id,
            limit=limit,
        )
        return [
            {
                "id": row.id,
                "artifact_type": row.artifact_type,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "created_by": row.created_by,
                "file_name": row.file_name,
                "content_type": row.content_type,
                "checksum": row.checksum,
                "reference_code": row.reference_code,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    def _build_result_sheet(self, attempt_id: str) -> dict:
        grading = GradingEngine(self._attempt_repo, self._exam_repo, self._question_repo)
        result = grading.get_admin_result(attempt_id)
        attempt = self._attempt_repo.get(attempt_id)
        if attempt is None:
            raise ResultExportError(f"Attempt '{attempt_id}' not found")
        exam = self._get_exam(attempt.exam_id)
        student = self._student_repo.get_student_auth_record(attempt.candidate_id) or {}
        topic_summary = self._topic_summary(result.get("question_results", []))
        analytics_summary = None
        if self._analytics_service is not None:
            try:
                analytics_summary = self._analytics_service.get_exam_analytics(exam.id)
            except Exception:
                analytics_summary = None
        return {
            "attempt_id": attempt_id,
            "student_id": attempt.candidate_id,
            "display_name": student.get("display_name") or attempt.candidate_id,
            "exam_id": exam.id,
            "exam_name": exam.name,
            "submitted_at": attempt.submitted_at,
            "total_score": result["total_score"],
            "total_possible_marks": result["total_possible_marks"],
            "percentage": result["percentage"],
            "passed": result["passed"],
            "graded_at": result["graded_at"],
            "question_results": result.get("question_results", []),
            "topic_summary": topic_summary,
            "results_published": exam.results_published,
            "results_published_at": exam.results_published_at,
            "results_published_by": exam.results_published_by,
            "reference_code": self._attempt_reference_code(exam.id, attempt_id),
            "analytics_summary": analytics_summary,
        }

    @staticmethod
    def _topic_summary(question_results: list[dict]) -> list[dict]:
        topic_map: dict[str, dict] = defaultdict(lambda: {"obtained": 0.0, "total": 0.0, "count": 0})
        for row in question_results:
            topic = str(row.get("topic") or "General").strip() or "General"
            topic_map[topic]["obtained"] += float(row.get("marks_awarded") or 0.0)
            topic_map[topic]["total"] += float(row.get("max_marks") or 0.0)
            topic_map[topic]["count"] += 1
        return [
            {
                "topic": topic,
                "obtained": round(values["obtained"], 2),
                "total": round(values["total"], 2),
                "count": values["count"],
            }
            for topic, values in sorted(topic_map.items(), key=lambda item: item[0].lower())
        ]

    def _render_result_html(self, sheet: dict) -> str:
        rows = "".join(
            f"<tr><td>{escape(item['topic'])}</td><td>{item['count']}</td><td>{item['obtained']:.2f}</td><td>{item['total']:.2f}</td></tr>"
            for item in sheet["topic_summary"]
        ) or "<tr><td colspan='4'>No topic summary available.</td></tr>"
        banner = ""
        if not sheet["results_published"]:
            banner = "<div class='banner'>UNPUBLISHED PREVIEW - Verify before publishing or exporting.</div>"
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NITMEXS Result Sheet</title>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; margin: 24px; color: #13203a; }}
    .sheet {{ max-width: 900px; margin: 0 auto; border: 1px solid #c6d4ef; border-radius: 16px; padding: 24px; }}
    .banner {{ margin-bottom: 16px; padding: 12px 14px; border-radius: 12px; background: #fff3cd; color: #6b4d00; font-weight: 700; }}
    .kicker {{ color: #2260d4; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; }}
    h1 {{ margin: 6px 0 2px; }}
    .muted {{ color: #5e6f91; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin: 18px 0; }}
    .card {{ border: 1px solid #d6e2f6; border-radius: 12px; padding: 12px; background: #f8fbff; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
    th, td {{ border-bottom: 1px solid #dbe6f7; text-align: left; padding: 9px 8px; }}
    .footer {{ margin-top: 24px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    @media print {{ .no-print {{ display:none; }} body {{ margin: 0; }} .sheet {{ border: none; }} }}
  </style>
</head>
<body>
  <section class="sheet">
    {banner}
    <p class="kicker">NITMEXS</p>
    <h1>Networked Integrated Training, Monitoring, Evaluation and eXamination Suite</h1>
    <p class="muted">Candidate Result Sheet</p>
    <div class="grid">
      <div class="card"><strong>Candidate</strong><br>{escape(str(sheet['display_name']))}<br>{escape(str(sheet['student_id']))}</div>
      <div class="card"><strong>Exam</strong><br>{escape(str(sheet['exam_name']))}<br>{escape(str(sheet['exam_id']))}</div>
      <div class="card"><strong>Score</strong><br>{sheet['total_score']:.2f} / {sheet['total_possible_marks']:.2f}<br>{sheet['percentage']:.2f}%</div>
      <div class="card"><strong>Result</strong><br>{'PASS' if sheet['passed'] else 'FAIL'}<br>Graded: {escape(str(sheet['graded_at']))}</div>
    </div>
    <h2>Topic Breakdown</h2>
    <table>
      <thead><tr><th>Topic</th><th>Questions</th><th>Obtained</th><th>Total</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <div class="footer">
      <div class="card"><strong>Publication</strong><br>Published: {escape(str(sheet['results_published_at'] or 'Pending'))}<br>Published by: {escape(str(sheet['results_published_by'] or 'Not published yet'))}</div>
      <div class="card"><strong>Verification</strong><br>Reference: {escape(str(sheet['reference_code']))}<br>Issued by: NITMEXS Exam Controller</div>
    </div>
    <p class="muted" style="margin-top:18px">Print this sheet or save as PDF from the browser print dialog.</p>
    <button class="no-print" onclick="window.print()">Print Result</button>
  </section>
</body>
</html>"""

    def _render_result_pdf(self, sheet: dict) -> bytes:
        lines = [
            "NITMEXS",
            "Networked Integrated Training, Monitoring, Evaluation and eXamination Suite",
            "",
            "Candidate Result Sheet",
            f"Candidate: {sheet['display_name']} ({sheet['student_id']})",
            f"Exam: {sheet['exam_name']} ({sheet['exam_id']})",
            f"Score: {sheet['total_score']:.2f} / {sheet['total_possible_marks']:.2f}",
            f"Percentage: {sheet['percentage']:.2f}%",
            f"Result: {'PASS' if sheet['passed'] else 'FAIL'}",
            f"Graded At: {sheet['graded_at']}",
            f"Published At: {sheet['results_published_at'] or 'Pending'}",
            f"Published By: {sheet['results_published_by'] or 'Pending'}",
            f"Reference: {sheet['reference_code']}",
            "",
            "Topic Breakdown:",
        ]
        for item in sheet["topic_summary"]:
            lines.append(
                f"- {item['topic']}: {item['obtained']:.2f}/{item['total']:.2f} across {item['count']} question(s)"
            )
        wrapped: list[str] = []
        for line in lines:
            wrapped.extend(textwrap.wrap(str(line), width=90) or [""])
        safe_lines = [self._pdf_escape(self._to_ascii(item)) for item in wrapped[:42]]
        content_lines = ["BT", "/F1 11 Tf", "50 790 Td"]
        first = True
        for line in safe_lines:
            if not first:
                content_lines.append("0 -16 Td")
            content_lines.append(f"({line}) Tj")
            first = False
        content_lines.append("ET")
        stream = "\n".join(content_lines).encode("latin-1")
        objects = [
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
            b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
            f"5 0 obj << /Length {len(stream)} >> stream\n".encode("latin-1") + stream + b"\nendstream endobj\n",
        ]
        buffer = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objects:
            offsets.append(len(buffer))
            buffer.extend(obj)
        xref_offset = len(buffer)
        buffer.extend(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
        buffer.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            buffer.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
        buffer.extend(
            (
                f"trailer << /Size {len(offsets)} /Root 1 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF"
            ).encode("latin-1")
        )
        return bytes(buffer)

    def _register_artifact(
        self,
        *,
        artifact_type: str,
        entity_type: str,
        entity_id: str,
        created_by: str,
        file_name: str,
        content_type: str,
        raw_bytes: bytes,
        reference_code: str,
    ) -> None:
        checksum = hashlib.sha256(raw_bytes).hexdigest()
        artifact = ResultArtifact(
            id=str(uuid.uuid4()),
            artifact_type=artifact_type,
            entity_type=entity_type,
            entity_id=entity_id,
            created_by=created_by,
            file_name=file_name,
            content_type=content_type,
            checksum=checksum,
            reference_code=reference_code,
            created_at=self._now_iso(),
        )
        self._artifact_repo.create(artifact)

    def _get_exam(self, exam_id: str):
        exam = self._exam_repo.get_exam(exam_id)
        if exam is None:
            raise ExamNotFoundError(f"Exam '{exam_id}' not found")
        return exam

    def _log_event(self, **kwargs) -> None:
        if self._audit_service is None:
            return
        try:
            self._audit_service.log_event(**kwargs)
        except Exception:
            return

    @staticmethod
    def _exam_reference_code(exam_id: str) -> str:
        return f"NMX-EX-{exam_id[:6].upper()}"

    @staticmethod
    def _attempt_reference_code(exam_id: str, attempt_id: str) -> str:
        return f"NMX-{exam_id[:4].upper()}-{attempt_id[:6].upper()}"

    @staticmethod
    def _pdf_escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    @staticmethod
    def _to_ascii(value: str) -> str:
        return str(value).encode("latin-1", errors="replace").decode("latin-1")

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
