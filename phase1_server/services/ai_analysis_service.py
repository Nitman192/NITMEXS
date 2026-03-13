"""AI-assisted exam analysis with deterministic offline fallback."""

from __future__ import annotations

import json
import os
from urllib import error as urllib_error
from urllib import request as urllib_request
from typing import Any

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None

try:
    from google import genai
except Exception:  # pragma: no cover - optional dependency
    genai = None


class AIAnalysisService:
    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
    ):
        requested_provider = provider or os.getenv("NITMEXS_AI_PROVIDER") or "auto"
        self._provider = requested_provider.strip().lower()
        self._model = (model or os.getenv("NITMEXS_AI_MODEL") or "").strip()

    @property
    def provider(self) -> str:
        candidates = self._provider_candidates()
        return candidates[0] if candidates else "heuristic"

    def status(self) -> dict[str, Any]:
        resolved = self.provider
        available = self._provider_candidates()

        reason = "heuristic_forced"
        if resolved == "heuristic":
            if self._provider in {"openai", "gemini"}:
                reason = f"{self._provider}_api_key_missing"
            elif self._provider == "auto":
                reason = "no_api_key_configured"
        elif resolved == "openai":
            reason = "live_openai_http_ready" if OpenAI is None else "live_openai_sdk_ready"
        elif resolved == "gemini":
            reason = "live_gemini_http_ready" if genai is None else "live_gemini_sdk_ready"

        return {
            "requested_provider": self._provider,
            "resolved_provider": resolved,
            "mode": "live" if resolved != "heuristic" else "fallback",
            "reason": reason,
            "available_providers": available,
            "model": self._default_model_for(resolved),
        }

    def explain_question(
        self,
        *,
        question_text: str,
        user_answer: str | None,
        correct_answer: str | None,
        topic: str | None,
        difficulty: str | None,
        status: str,
    ) -> dict[str, Any]:
        fallback = self._heuristic_question_explanation(
            question_text=question_text,
            user_answer=user_answer,
            correct_answer=correct_answer,
            topic=topic,
            difficulty=difficulty,
            status=status,
        )
        attempted: list[str] = []
        prompt = self._question_prompt(
            question_text=question_text,
            user_answer=user_answer,
            correct_answer=correct_answer,
            topic=topic,
            difficulty=difficulty,
            status=status,
        )
        for candidate in self._provider_candidates():
            attempted.append(candidate)
            text = self._openai_json(prompt) if candidate == "openai" else self._gemini_text(prompt)
            parsed = self._parse_json_dict(text)
            if parsed:
                return {
                    **fallback,
                    **parsed,
                    "provider": candidate,
                    "provider_status": self._live_status(candidate),
                }
        return {
            **fallback,
            "provider_status": self._fallback_status(attempted),
        }

    def summarize_attempt(self, incorrect_rows: list[dict[str, Any]]) -> dict[str, Any]:
        fallback = self._heuristic_attempt_summary(incorrect_rows)
        if not incorrect_rows:
            return {
                **fallback,
                "provider_status": self.status(),
            }

        attempted: list[str] = []
        prompt = self._attempt_summary_prompt(incorrect_rows)
        for candidate in self._provider_candidates():
            attempted.append(candidate)
            text = self._openai_json(prompt) if candidate == "openai" else self._gemini_text(prompt)
            parsed = self._parse_json_dict(text)
            if parsed:
                return {
                    **fallback,
                    **parsed,
                    "provider": candidate,
                    "provider_status": self._live_status(candidate),
                }

        return {
            **fallback,
            "provider_status": self._fallback_status(attempted),
        }

    def _heuristic_question_explanation(
        self,
        *,
        question_text: str,
        user_answer: str | None,
        correct_answer: str | None,
        topic: str | None,
        difficulty: str | None,
        status: str,
    ) -> dict[str, Any]:
        normalized_topic = (topic or "general concepts").strip() or "general concepts"
        difficulty_label = (difficulty or "standard").strip() or "standard"
        if status == "skipped":
            why_wrong = (
                "Question skip hone ki wajah se score capture nahi hua. Yeh usually time pressure, uncertainty, ya concept recall gap ka signal hota hai."
            )
        else:
            why_wrong = (
                f"Selected answer '{user_answer or 'No answer'}' expected concept ko match nahi karta. Correct answer '{correct_answer or 'Unavailable'}' is question ke key idea ko better satisfy karta hai."
            )
        return {
            "provider": "heuristic",
            "why_wrong": why_wrong,
            "core_concept": (
                f"Is question ka core concept '{normalized_topic}' topic ka {difficulty_label} level application hai. Concept clarity + option elimination dono important the."
            ),
            "study_tip": (
                f"Next time '{normalized_topic}' par 10-15 targeted practice questions solve karo aur har wrong answer ke saath ek one-line rule note banao."
            ),
            "weak_topic": normalized_topic,
            "learning_step": (
                f"{normalized_topic} ko revision -> solved examples -> timed mini-quiz sequence me revise karo."
            ),
        }

    def _heuristic_attempt_summary(self, incorrect_rows: list[dict[str, Any]]) -> dict[str, Any]:
        topic_map: dict[str, dict[str, Any]] = {}
        skipped = 0
        incorrect = 0
        for row in incorrect_rows:
            topic = str(row.get("topic") or "untagged").strip() or "untagged"
            entry = topic_map.setdefault(
                topic,
                {
                    "topic": topic,
                    "count": 0,
                    "skipped_count": 0,
                    "incorrect_count": 0,
                    "recommended_focus": "",
                },
            )
            entry["count"] += 1
            if str(row.get("status")) == "skipped":
                entry["skipped_count"] += 1
                skipped += 1
            else:
                entry["incorrect_count"] += 1
                incorrect += 1

        weak_topics = sorted(
            topic_map.values(),
            key=lambda item: (item["count"], item["incorrect_count"]),
            reverse=True,
        )
        for item in weak_topics:
            if item["skipped_count"] > item["incorrect_count"]:
                item["recommended_focus"] = (
                    f"{item['topic']} me time-boxed attempt drills karo, taaki uncertainty ki wajah se skip na ho."
                )
            else:
                item["recommended_focus"] = (
                    f"{item['topic']} me concept recap ke baad error-log based practice set complete karo."
                )

        learning_path = [
            "Top 2 weak topics identify karke 30-minute concept revision slots schedule karo.",
            "Har weak topic ke liye 10 solved examples aur 15 timed MCQs complete karo.",
            "Next mock me pehle easy-confidence questions lock karo, phir doubtful set revisit karo.",
        ]
        if skipped:
            learning_path.append(
                "Skip pattern reduce karne ke liye 2-pass strategy follow karo: first pass sure answers, second pass calculated attempts."
            )
        if incorrect:
            learning_path.append(
                "Wrong-answer notebook maintain karo jahan har mistake ke saath ek crisp correction rule likho."
            )

        return {
            "provider": "heuristic",
            "summary": (
                f"{len(incorrect_rows)} weak-response question(s) detect hui. Sabse zyada attention {', '.join(item['topic'] for item in weak_topics[:3]) or 'revision discipline'} ko chahiye."
            ),
            "weak_topics": weak_topics[:5],
            "learning_path": learning_path[:6],
        }

    def _question_prompt(
        self,
        *,
        question_text: str,
        user_answer: str | None,
        correct_answer: str | None,
        topic: str | None,
        difficulty: str | None,
        status: str,
    ) -> str:
        return (
            "You are an exam analysis tutor. Return exactly one valid JSON object and no markdown. "
            "Use only these keys: "
            "why_wrong, core_concept, study_tip, weak_topic, learning_step. "
            f"Question: {question_text}\n"
            f"Topic: {topic or 'untagged'}\n"
            f"Difficulty: {difficulty or 'unknown'}\n"
            f"Attempt status: {status}\n"
            f"Student answer: {user_answer or 'Skipped'}\n"
            f"Correct answer: {correct_answer or 'Unavailable'}"
        )

    def _attempt_summary_prompt(self, incorrect_rows: list[dict[str, Any]]) -> str:
        compact_rows = [
            {
                "question_id": row.get("question_id"),
                "topic": row.get("topic"),
                "status": row.get("status"),
                "question_text": row.get("question_text"),
            }
            for row in incorrect_rows[:30]
        ]
        return (
            "You are an exam performance coach. Return exactly one valid JSON object and no markdown. "
            "Use only these keys: "
            "summary, weak_topics, learning_path. weak_topics must be a JSON array of "
            "objects with topic, count, skipped_count, incorrect_count, recommended_focus. "
            "learning_path must be an array of concise steps.\n"
            f"Question outcomes: {json.dumps(compact_rows, ensure_ascii=True)}"
        )

    def _provider_candidates(self) -> list[str]:
        if self._provider == "openai":
            return ["openai"] if self._openai_enabled() else []
        if self._provider == "gemini":
            return ["gemini"] if self._gemini_enabled() else []
        candidates: list[str] = []
        if self._openai_enabled():
            candidates.append("openai")
        if self._gemini_enabled():
            candidates.append("gemini")
        return candidates

    def _live_status(self, provider: str) -> dict[str, Any]:
        status = self.status()
        return {
            **status,
            "resolved_provider": provider,
            "mode": "live",
            "reason": (
                "live_openai_http_ready"
                if provider == "openai" and OpenAI is None
                else "live_openai_sdk_ready"
                if provider == "openai"
                else "live_gemini_http_ready"
                if genai is None
                else "live_gemini_sdk_ready"
            ),
            "model": self._default_model_for(provider),
        }

    def _fallback_status(self, attempted: list[str]) -> dict[str, Any]:
        if not attempted:
            return self.status()
        return {
            **self.status(),
            "resolved_provider": "heuristic",
            "mode": "fallback",
            "reason": f"{attempted[-1]}_request_failed_or_invalid_json",
            "attempted_providers": attempted,
            "model": self._default_model_for(attempted[-1]),
        }

    def _openai_enabled(self) -> bool:
        return bool(os.getenv("NITMEXS_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))

    def _gemini_enabled(self) -> bool:
        return bool(os.getenv("NITMEXS_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY"))

    def _openai_json(self, prompt: str) -> str | None:
        api_key = os.getenv("NITMEXS_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        if OpenAI is None:
            return self._openai_http(prompt, api_key)
        try:
            client = OpenAI(api_key=api_key)
            response = client.responses.create(
                model=self._default_model_for("openai"),
                input=prompt,
            )
            output_text = getattr(response, "output_text", None)
            if isinstance(output_text, str) and output_text.strip():
                return output_text.strip()
            output = getattr(response, "output", None) or []
            parts: list[str] = []
            for item in output:
                for content in getattr(item, "content", None) or []:
                    text = getattr(content, "text", None)
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            return "\n".join(parts).strip() or None
        except Exception:
            return self._openai_http(prompt, api_key)

    def _gemini_text(self, prompt: str) -> str | None:
        api_key = os.getenv("NITMEXS_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        if genai is None:
            return self._gemini_http(prompt, api_key)
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=self._default_model_for("gemini"),
                contents=prompt,
            )
            text = getattr(response, "text", None)
            if isinstance(text, str) and text.strip():
                return text.strip()
            return None
        except Exception:
            return self._gemini_http(prompt, api_key)

    def _openai_http(self, prompt: str, api_key: str) -> str | None:
        payload = {
            "model": self._default_model_for("openai"),
            "input": prompt,
            "store": False,
        }
        data = self._post_json(
            url="https://api.openai.com/v1/responses",
            body=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        if not isinstance(data, dict):
            return None
        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()
        output = data.get("output") or []
        parts: list[str] = []
        for item in output if isinstance(output, list) else []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content") or []:
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip() or None

    def _gemini_http(self, prompt: str, api_key: str) -> str | None:
        model = self._default_model_for("gemini")
        data = self._post_json(
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            body={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt,
                            }
                        ]
                    }
                ]
            },
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
        )
        if not isinstance(data, dict):
            return None
        candidates = data.get("candidates") or []
        for candidate in candidates if isinstance(candidates, list) else []:
            if not isinstance(candidate, dict):
                continue
            content = candidate.get("content") or {}
            if not isinstance(content, dict):
                continue
            for part in content.get("parts") or []:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
        return None

    def _post_json(self, url: str, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any] | None:
        request = urllib_request.Request(
            url=url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=25) as response:
                payload = response.read().decode("utf-8")
        except (urllib_error.HTTPError, urllib_error.URLError, TimeoutError):
            return None
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _default_model_for(self, provider: str) -> str:
        if provider == "openai":
            return self._model or os.getenv("NITMEXS_OPENAI_MODEL") or "gpt-4.1-mini"
        if provider == "gemini":
            return self._model or os.getenv("NITMEXS_GEMINI_MODEL") or "gemini-2.5-flash"
        return self._model or "heuristic"

    def _parse_json_dict(self, text: str | None) -> dict[str, Any] | None:
        if not text:
            return None
        raw = text.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
