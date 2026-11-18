import os
import json
import logging
from typing import Dict, Any, Tuple, Optional
from config.config import Config

logger = logging.getLogger(__name__)


class LLMClient:
    """Provider-independent LLM interface with deterministic fallback logic."""

    def __init__(
        self,
        provider: str = Config.LLM_PROVIDER,
        model: str = Config.LLM_MODEL
    ):
        self.provider = provider.lower()
        self.model = model
        self.gemini_key = Config.GEMINI_API_KEY
        self.openai_key = Config.OPENAI_API_KEY

    def is_llm_enabled(self) -> bool:
        """Check if a real external LLM API is configured with valid credentials."""
        if self.provider == "gemini" and self.gemini_key:
            return True
        if self.provider == "openai" and self.openai_key:
            return True
        return False

    def query_json(
        self,
        prompt: str,
        system_instruction: str = "You are a software engineering diagnostic assistant."
    ) -> Tuple[Dict[str, Any], str]:
        """Query LLM for structured JSON output or return empty if in offline mode."""
        if not self.is_llm_enabled():
            return {}, "rule-based-fallback"

        if self.provider == "gemini":
            return self._query_gemini(prompt, system_instruction)
        elif self.provider == "openai":
            return self._query_openai(prompt, system_instruction)

        return {}, "rule-based-fallback"

    def _query_gemini(self, prompt: str, system_instruction: str) -> Tuple[Dict[str, Any], str]:
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }
        try:
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text), "llm-powered"
            else:
                logger.warning(f"Gemini API error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Failed to query Gemini API: {e}")

        return {}, "rule-based-fallback"

    def _query_openai(self, prompt: str, system_instruction: str) -> Tuple[Dict[str, Any], str]:
        import requests
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                return json.loads(text), "llm-powered"
            else:
                logger.warning(f"OpenAI API error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Failed to query OpenAI API: {e}")

        return {}, "rule-based-fallback"
