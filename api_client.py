"""HTTP client for the NITMEXS desktop application."""

from __future__ import annotations

from dataclasses import dataclass

import httpx


class ApiError(Exception):
    """Raised when backend API calls fail."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass(frozen=True)
class ExamItem:
    exam_id: str
    name: str
    duration_minutes: int


class NITMEXSApiClient:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip("/")

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_data: dict | None = None,
    ) -> dict:
        with httpx.Client(base_url=self._base_url, timeout=20.0) as client:
            response = client.request(method, path, headers=headers, json=json_data)

        if response.status_code >= 400:
            detail = "Request failed"
            try:
                body = response.json()
                detail = body.get("detail") or detail
            except Exception:
                detail = response.text or detail
            raise ApiError(response.status_code, detail)

        return response.json().get("data", {})

    def list_published_exams(self) -> list[ExamItem]:
        data = self._request("GET", "/admin/exams", headers={"x-admin": "true"})
        exams: list[ExamItem] = []
        for exam in data:
            if exam.get("published") or exam.get("status") == "ACTIVE":
                exams.append(
                    ExamItem(
                        exam_id=exam["id"],
                        name=exam["name"],
                        duration_minutes=int(exam["duration_minutes"]),
                    )
                )
        return exams

    def start_exam(self, student_id: str, exam_id: str) -> dict:
        return self._request(
            "POST",
            f"/student/exams/{exam_id}/start",
            headers={"x-student-id": student_id},
        )

    def fetch_question(self, student_id: str, attempt_id: str, sequence_number: int) -> dict:
        return self._request(
            "GET",
            f"/student/attempts/{attempt_id}/questions/{sequence_number}",
            headers={"x-student-id": student_id},
        )

    def submit_answer(
        self,
        student_id: str,
        attempt_id: str,
        question_id: str,
        selected_option_id: str,
    ) -> dict:
        return self._request(
            "POST",
            f"/student/attempts/{attempt_id}/answers",
            headers={"x-student-id": student_id},
            json_data={
                "question_id": question_id,
                "selected_option_id": selected_option_id,
            },
        )

    def finalize_exam(self, student_id: str, attempt_id: str) -> dict:
        return self._request(
            "POST",
            f"/student/attempts/{attempt_id}/finalize",
            headers={"x-student-id": student_id},
        )

    def get_result(self, student_id: str, attempt_id: str) -> dict:
        return self._request(
            "GET",
            f"/student/attempts/{attempt_id}/result",
            headers={"x-student-id": student_id},
        )
