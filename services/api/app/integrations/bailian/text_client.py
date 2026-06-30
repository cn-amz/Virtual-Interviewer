from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx


HttpPost = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class BailianTextConfig:
    api_key: str | None
    model: str = "qwen3.6-plus"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class BailianTextClient:
    def __init__(
        self,
        config: BailianTextConfig,
        system_prompt: str,
        http_post: HttpPost | None = None,
    ) -> None:
        self._config = config
        self._system_prompt = system_prompt
        self._http_post = http_post
        self._history: list[dict[str, str]] = []

    @property
    def history(self) -> list[dict[str, str]]:
        return list(self._history)

    def add_to_history(self, role: str, content: str) -> None:
        self._history.append({"role": role, "content": content})

    async def next_question(self) -> str:
        if not self._config.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is required for Bailian text mode.")

        messages = [{"role": "system", "content": self._system_prompt}, *self._history]
        response = await self._post(
            self._chat_url(),
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._config.model,
                "messages": messages,
                "temperature": 0.6,
                "max_tokens": 220,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        try:
            content = str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Bailian text response did not contain assistant content.") from exc
        self._history.append({"role": "assistant", "content": content})
        return content

    async def _post(self, *args: Any, **kwargs: Any):
        if self._http_post:
            return await self._http_post(*args, **kwargs)
        async with httpx.AsyncClient() as client:
            return await client.post(*args, **kwargs)

    def _chat_url(self) -> str:
        return f"{self._config.base_url.rstrip('/')}/chat/completions"
