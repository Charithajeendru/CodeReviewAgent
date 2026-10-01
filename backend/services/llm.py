from __future__ import annotations

import json
from typing import Any

import httpx

from backend.config import settings


class LLMServiceError(RuntimeError):
    pass


def sanitize_untrusted_code(code: str) -> str:
    """Treat source text as data rather than executable instructions.

    Our security model never lets source code override system instructions.
    In the initial build we preserve the text intact and strip obvious control bytes.
    """
    if not isinstance(code, str):
        return str(code)
    return code.replace("\x00", "").strip()


def validate_structured_output(raw_output: str, expected_keys: list[str] | None = None) -> dict[str, Any]:
    """Safely parse LLM JSON output and reject malformed payloads."""
    if not isinstance(raw_output, str):
        return {}

    raw_output = raw_output.strip()
    if not raw_output:
        return {}

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return {}

    if not isinstance(parsed, dict):
        return {}

    if expected_keys is not None:
        if not all(key in parsed for key in expected_keys):
            return {}

    return parsed


class LLMService:
    def __init__(self) -> None:
        self.provider = settings.llm_provider
        self.model = settings.llm_model
        self.api_key = settings.llm_api_key

    @property
    def available(self) -> bool:
        return self.provider.casefold() == "openai" and bool(self.api_key)

    def _fallback_response(self, prompt: str) -> str:
        return json.dumps(
            {
                "status": "stub",
                "prompt": prompt[:400],
                "note": "LLM provider is not configured; returning deterministic fallback analysis.",
            }
        )

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if self.provider == "stub" or not self.api_key:
            return self._fallback_response(prompt)
        if self.provider.casefold() != "openai":
            raise LLMServiceError("Configured AI provider is not supported.")

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    url="https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                return payload["choices"][0]["message"]["content"]
        except Exception as exc:
            raise LLMServiceError("AI provider request failed.") from exc

    async def generate_structured(
        self,
        prompt: str,
        expected_keys: list[str],
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        raw_output = await self.generate(prompt, system_prompt)
        parsed = validate_structured_output(raw_output, expected_keys)
        if not parsed:
            raise LLMServiceError("AI provider returned invalid structured output.")
        return parsed

    @staticmethod
    def parse_json(text: str, default: Any | None = None) -> Any:
        try:
            return json.loads(text)
        except Exception:
            if default is not None:
                return default
            return {"raw": text}


llm_service = LLMService()
