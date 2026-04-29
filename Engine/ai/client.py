from __future__ import annotations

import json
import os
import time
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - dependency may be absent in test env
    OpenAI = None


class DeepSeekClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = base_url or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")
        self.timeout_seconds = float(os.environ.get("DEEPSEEK_TIMEOUT_SECONDS", "180"))
        self.max_retries = int(os.environ.get("DEEPSEEK_MAX_RETRIES", "3"))
        self.retry_delay_seconds = float(os.environ.get("DEEPSEEK_RETRY_DELAY_SECONDS", "4"))
        self._client = None
        if OpenAI is not None and self.api_key:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @property
    def available(self) -> bool:
        return self._client is not None

    def complete(self, messages: list[dict[str, str]], *, reasoning_effort: str = "high") -> str | None:
        if self._client is None:
            return None
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=False,
                    timeout=self.timeout_seconds,
                    reasoning_effort=reasoning_effort,
                    extra_body={"thinking": {"type": "enabled"}},
                )
                choice = response.choices[0].message
                return choice.content if choice is not None else None
            except Exception as exc:  # pragma: no cover - depends on live API failures
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.retry_delay_seconds)
        return None

    def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        reasoning_effort: str = "high",
    ) -> dict[str, Any] | None:
        content = self.complete(messages, reasoning_effort=reasoning_effort)
        if not content:
            return None
        return self._extract_json(content)

    def _extract_json(self, content: str) -> dict[str, Any] | None:
        content = content.strip()
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                return None
