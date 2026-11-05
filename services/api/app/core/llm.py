"""Thin LLM client. The ONLY place that talks to the model provider.

Live: Azure AI Foundry OpenAI-compatible v1 endpoint (Bearer key) via the OpenAI SDK.
Fake: deterministic canned responses so tests and offline demos never need the network.
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.core.config import get_settings


class LLMClient:
    def __init__(self) -> None:
        s = get_settings()
        self.model = s.llm_model
        self.live = s.llm_live
        self._client = OpenAI(base_url=s.azure_endpoint_url.rstrip("/"), api_key=s.azure_api_key) if self.live else None

    def chat(self, messages: list[dict], tools: list[dict] | None = None, **kw: Any):
        """Returns the raw OpenAI ChatCompletion message (live) or a fake one."""
        if not self.live:
            return _fake_message(messages)
        resp = self._client.chat.completions.create(
            model=self.model, messages=messages, tools=tools or None, max_completion_tokens=kw.get("max_tokens", 4096)
        )
        return resp.choices[0].message

    def json(self, system: str, user: str, max_tokens: int = 4096) -> dict:
        """Structured JSON output (used for document extraction)."""
        if not self.live:
            return {"_fake": True}
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            max_completion_tokens=max_tokens,
        )
        return json.loads(resp.choices[0].message.content or "{}")


class _FakeMsg:
    def __init__(self, content: str):
        self.content = content
        self.tool_calls = None
        self.role = "assistant"


def _fake_message(messages: list[dict]) -> _FakeMsg:
    last = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    return _FakeMsg(f"[Offline-Modus] Ich habe Ihre Nachricht erhalten: „{last[:120]}“.")


def get_llm() -> LLMClient:
    return LLMClient()


if __name__ == "__main__":  # smoke test: uv run python -m app.core.llm
    c = get_llm()
    print("live" if c.live else "fake", c.model)
    print(c.chat([{"role": "user", "content": "Antworte nur mit: ok"}]).content)
