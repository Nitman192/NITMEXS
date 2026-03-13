import os
import unittest
from unittest import mock

import phase1_server.services.ai_analysis_service as ai_module
from phase1_server.services.ai_analysis_service import AIAnalysisService


class AIAnalysisServiceTests(unittest.TestCase):
    def test_openai_http_provider_selected_when_key_available(self):
        with mock.patch.dict(
            os.environ,
            {
                "NITMEXS_AI_PROVIDER": "openai",
                "NITMEXS_OPENAI_API_KEY": "test-openai-key",
            },
            clear=True,
        ):
            with mock.patch.object(ai_module, "OpenAI", None):
                service = AIAnalysisService()
                service._openai_http = lambda prompt, api_key: (
                    '{"why_wrong":"Mismatch","core_concept":"Forms","study_tip":"Revise control labels","weak_topic":"VB UI","learning_step":"Practice 10 MCQs"}'
                )
                payload = service.explain_question(
                    question_text="Which control displays the result of an expression?",
                    user_answer="Bound Control",
                    correct_answer="Label",
                    topic="VB UI",
                    difficulty="easy",
                    status="incorrect",
                )

        self.assertEqual(payload["provider"], "openai")
        self.assertEqual(payload["provider_status"]["resolved_provider"], "openai")
        self.assertEqual(payload["provider_status"]["mode"], "live")
        self.assertEqual(payload["study_tip"], "Revise control labels")

    def test_auto_provider_falls_back_to_gemini_after_openai_failure(self):
        with mock.patch.dict(
            os.environ,
            {
                "NITMEXS_AI_PROVIDER": "auto",
                "NITMEXS_OPENAI_API_KEY": "test-openai-key",
                "NITMEXS_GEMINI_API_KEY": "test-gemini-key",
            },
            clear=True,
        ):
            with mock.patch.object(ai_module, "OpenAI", None), mock.patch.object(
                ai_module, "genai", None
            ):
                service = AIAnalysisService()
                service._openai_http = lambda prompt, api_key: None
                service._gemini_http = lambda prompt, api_key: (
                    '{"summary":"Weak topic cluster found.","weak_topics":[{"topic":"Networking","count":1,"skipped_count":0,"incorrect_count":1,"recommended_focus":"Revise TCP/IP basics"}],"learning_path":["Revise OSI layers","Solve 15 timed questions"]}'
                )
                payload = service.summarize_attempt(
                    [
                        {
                            "question_id": "q-1",
                            "topic": "Networking",
                            "status": "incorrect",
                            "question_text": "Which layer handles routing?",
                        }
                    ]
                )

        self.assertEqual(payload["provider"], "gemini")
        self.assertEqual(payload["provider_status"]["resolved_provider"], "gemini")
        self.assertEqual(payload["provider_status"]["mode"], "live")
        self.assertEqual(payload["weak_topics"][0]["topic"], "Networking")

    def test_provider_failure_surfaces_fallback_reason(self):
        with mock.patch.dict(
            os.environ,
            {
                "NITMEXS_AI_PROVIDER": "openai",
                "NITMEXS_OPENAI_API_KEY": "test-openai-key",
            },
            clear=True,
        ):
            with mock.patch.object(ai_module, "OpenAI", None):
                service = AIAnalysisService()
                service._openai_http = lambda prompt, api_key: "not valid json"
                payload = service.explain_question(
                    question_text="Which control displays the result of an expression?",
                    user_answer="Bound Control",
                    correct_answer="Label",
                    topic="VB UI",
                    difficulty="easy",
                    status="incorrect",
                )

        self.assertEqual(payload["provider"], "heuristic")
        self.assertEqual(
            payload["provider_status"]["reason"],
            "openai_request_failed_or_invalid_json",
        )
        self.assertEqual(payload["provider_status"]["mode"], "fallback")


if __name__ == "__main__":
    unittest.main()
