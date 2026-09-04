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
        return await self._complete(
            messages,
            temperature=0.6,
            max_tokens=220,
            record_assistant=True,
        )

    async def analyze_report(self, prompt: str) -> str:
        if not self._config.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is required for Bailian report analysis.")
        return await self._complete(
            [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=900,
            record_assistant=False,
        )

    async def organize_ability_tree(self, prompt: str) -> str:
        if not self._config.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is required for ability tree organization.")
        return await self._complete(
            [
                {"role": "system", "content": "你是能力树整理器，只输出符合要求的 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1600,
            record_assistant=False,
        )

    async def analyze_job_description(self, prompt: str) -> str:
        if not self._config.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is required for job description analysis.")
        return await self._complete(
            [
                {"role": "system", "content": "你是岗位方向分析器，只输出符合要求的 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1400,
            record_assistant=False,
        )

    async def _complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        record_assistant: bool,
    ) -> str:
        response = await self._post(
            self._chat_url(),
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._config.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        try:
            content = str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Bailian text response did not contain assistant content.") from exc
        if record_assistant:
            self._history.append({"role": "assistant", "content": content})
        return content

    async def _post(self, *args: Any, **kwargs: Any):
        if self._http_post:
            return await self._http_post(*args, **kwargs)
        async with httpx.AsyncClient() as client:
            return await client.post(*args, **kwargs)

    def _chat_url(self) -> str:
        return f"{self._config.base_url.rstrip('/')}/chat/completions"
