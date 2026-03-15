"""Offline local-sidecar AI assistance for admin workflows."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from phase1_server.settings import AppSettings


class LocalAIError(ValueError):
    pass


@dataclass(frozen=True)
class LocalAIStatus:
    enabled: bool
    mode: str
    provider: str
    model_name: str
    base_url: str
    timeout_seconds: int
    reachable: bool
    reason: str
    available_features: list[str]
    discovered_models: list[str]


class LocalAISidecarService:
    def __init__(self, settings: AppSettings):
        self._settings = settings

    def status(self) -> dict:
        base_url = (self._settings.ai_base_url or "").strip()
        features = self.enabled_features()
        if self._settings.ai_mode != "local_sidecar":
            return LocalAIStatus(
                enabled=False,
                mode=self._settings.ai_mode,
                provider="local_http",
                model_name=self._settings.ai_model_name,
                base_url=base_url,
                timeout_seconds=self._settings.ai_timeout_seconds,
                reachable=False,
                reason="local_sidecar_mode_disabled",
                available_features=features,
                discovered_models=[],
            ).__dict__
        if not self._is_local_url(base_url):
            return LocalAIStatus(
                enabled=False,
                mode=self._settings.ai_mode,
                provider="local_http",
                model_name=self._settings.ai_model_name,
                base_url=base_url,
                timeout_seconds=self._settings.ai_timeout_seconds,
                reachable=False,
                reason="base_url_must_point_to_localhost",
                available_features=features,
                discovered_models=[],
            ).__dict__
        discovered_models: list[str] = []
        try:
            payload = self._http_json("GET", "/api/tags")
            discovered_models = [
                str(item.get("name") or "").strip()
                for item in payload.get("models", [])
                if str(item.get("name") or "").strip()
            ]
            return LocalAIStatus(
                enabled=True,
                mode=self._settings.ai_mode,
                provider="local_http",
                model_name=self._settings.ai_model_name,
                base_url=base_url,
                timeout_seconds=self._settings.ai_timeout_seconds,
                reachable=True,
                reason="sidecar_reachable",
                available_features=features,
                discovered_models=discovered_models,
            ).__dict__
        except Exception as exc:
            return LocalAIStatus(
                enabled=True,
                mode=self._settings.ai_mode,
                provider="local_http",
                model_name=self._settings.ai_model_name,
                base_url=base_url,
                timeout_seconds=self._settings.ai_timeout_seconds,
                reachable=False,
                reason=f"sidecar_unreachable:{type(exc).__name__}",
                available_features=features,
                discovered_models=discovered_models,
            ).__dict__

    def enabled_features(self) -> list[str]:
        raw = getattr(self._settings, "ai_enabled_features", "") or ""
        return [item.strip() for item in str(raw).split(",") if item.strip()]

    def refine_question(
        self,
        *,
        question_text: str,
        question_type: str,
        topic: str,
        marks: float,
    ) -> dict:
        fallback = {
            "provider": "heuristic",
            "rewritten_question": question_text.strip(),
            "clarity_notes": [
                "Question stem ko direct aur single-intent rakhna best hota hai.",
                "Topic aur asked action ko clearly separate rakhna readability improve karta hai.",
            ],
            "ambiguity_flags": [],
        }
        prompt = (
            "Return exactly one JSON object with keys rewritten_question, clarity_notes, ambiguity_flags. "
            f"Question type: {question_type}\nTopic: {topic}\nMarks: {marks}\n"
            f"Question text: {question_text}"
        )
        parsed = self._ask_json(prompt)
        return {**fallback, **parsed} if parsed else fallback

    def suggest_rubric(
        self,
        *,
        question_text: str,
        question_type: str,
        max_marks: float,
    ) -> dict:
        fallback = {
            "provider": "heuristic",
            "rubric_points": [
                "Concept definition or main idea",
                "Correct explanation or process",
                "Relevant example or application",
            ],
            "marker_guidance": f"Marks should stay within 0 to {max_marks}.",
        }
        prompt = (
            "Return exactly one JSON object with keys rubric_points, marker_guidance. "
            f"Question type: {question_type}\nMax marks: {max_marks}\nQuestion: {question_text}"
        )
        parsed = self._ask_json(prompt)
        return {**fallback, **parsed} if parsed else fallback

    def cluster_fib_answers(
        self,
        *,
        question_text: str,
        answers: list[str],
    ) -> dict:
        normalized_counts = Counter(self._normalize_text(item) for item in answers if self._normalize_text(item))
        fallback = {
            "provider": "heuristic",
            "summary": f"{len(normalized_counts)} distinct normalized FIB answer group(s) found.",
            "clusters": [
                {
                    "normalized_answer": answer,
                    "submission_count": count,
                    "suggested_decision": "review",
                }
                for answer, count in normalized_counts.most_common(10)
            ],
        }
        prompt = (
            "Return exactly one JSON object with keys summary, clusters. "
            "Each cluster item must contain normalized_answer, submission_count, suggested_decision. "
            f"Question: {question_text}\nSubmitted answers: {json.dumps(answers[:80])}"
        )
        parsed = self._ask_json(prompt)
        return {**fallback, **parsed} if parsed else fallback

    def suggest_subjective_score(
        self,
        *,
        question_text: str,
        question_type: str,
        answer_text: str,
        max_marks: float,
    ) -> dict:
        fallback = {
            "provider": "heuristic",
            "suggested_marks": round(max_marks * 0.6, 2),
            "reasoning": "Answer ko examiner review ke liye summarize karke mid-band suggestion diya gaya hai.",
            "review_note": "Manual verification required before final marks are saved.",
        }
        prompt = (
            "Return exactly one JSON object with keys suggested_marks, reasoning, review_note. "
            f"Question type: {question_type}\nMax marks: {max_marks}\nQuestion: {question_text}\n"
            f"Student answer: {answer_text}"
        )
        parsed = self._ask_json(prompt)
        if parsed and "suggested_marks" in parsed:
            try:
                parsed["suggested_marks"] = max(0.0, min(float(parsed["suggested_marks"]), float(max_marks)))
            except Exception:
                parsed["suggested_marks"] = fallback["suggested_marks"]
        return {**fallback, **parsed} if parsed else fallback

    def summarize_exam_analytics(
        self,
        *,
        exam_name: str,
        analytics_payload: dict,
    ) -> dict:
        summary = analytics_payload.get("summary", {})
        fallback = {
            "provider": "heuristic",
            "summary_text": (
                f"{exam_name} me total attempts {summary.get('total_attempts', 0)} rahe. "
                f"Mean score {summary.get('mean_score', 0):.2f} aur pass rate {summary.get('pass_rate', 0):.1f}% record hua."
            ),
            "action_points": [
                "Weak topics ko next remedial session me prioritize karo.",
                "Low-performing questions ka wording/rubric review karo.",
                "Pending review items close karke results publish karo.",
            ],
        }
        prompt = (
            "Return exactly one JSON object with keys summary_text, action_points. "
            f"Exam name: {exam_name}\nAnalytics JSON: {json.dumps(analytics_payload)[:7000]}"
        )
        parsed = self._ask_json(prompt)
        return {**fallback, **parsed} if parsed else fallback

    def _ask_json(self, prompt: str) -> dict | None:
        status = self.status()
        if not status.get("reachable"):
            return None
        try:
            payload = self._http_json(
                "POST",
                "/api/generate",
                {
                    "model": self._settings.ai_model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
        except Exception:
            return None
        raw_text = str(payload.get("response") or "").strip()
        if not raw_text:
            return None
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def _http_json(self, method: str, path: str, payload: dict | None = None) -> dict:
        base_url = self._settings.ai_base_url.rstrip("/")
        url = f"{base_url}{path}"
        body = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        request = urllib_request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib_request.urlopen(request, timeout=self._settings.ai_timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except urllib_error.URLError as exc:
            raise LocalAIError(str(exc)) from exc
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            raise LocalAIError("AI sidecar returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise LocalAIError("AI sidecar returned unexpected payload")
        return data

    @staticmethod
    def _is_local_url(url: str) -> bool:
        try:
            parsed = urllib_parse.urlparse(url)
        except Exception:
            return False
        return parsed.hostname in {"127.0.0.1", "localhost", "::1"}

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = " ".join(
            "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in str(value or "")).split()
        )
        return normalized.strip()
