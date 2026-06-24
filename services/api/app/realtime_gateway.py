from __future__ import annotations

import inspect
from collections.abc import Awaitable
from typing import Any


class RealtimeGateway:
    """Dispatch normalized interview events to the active realtime backend."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def start_events(self) -> list[dict]:
        if not hasattr(self._session, "start_events"):
            return []
        events = self._session.start_events()
        return await self._resolve(events)

    async def dispatch(self, event: dict) -> list[dict]:
        event_type = event.get("type", "")
        try:
            if event_type == "text.input":
                return await self._call("handle_text", str(event.get("text", "")))

            if event_type == "audio.start":
                return await self._dispatch_audio_start(event)

            if event_type == "audio.chunk":
                return await self._dispatch_audio_chunk(event)

            if event_type == "audio.stop":
                return await self._dispatch_audio_stop()

            if event_type == "session.end":
                return await self._call("handle_session_end")
        except Exception as exc:
            return [{"type": "realtime.error", "message": str(exc)}]

        return []

    async def _dispatch_audio_start(self, event: dict) -> list[dict]:
        mime_type = str(event.get("mime_type", "audio/webm"))
        sample_rate = event.get("sample_rate")
        if hasattr(self._session, "handle_audio_start"):
            return await self._call("handle_audio_start", mime_type, sample_rate)
        return await self._call("send_audio_start", mime_type, sample_rate)

    async def _dispatch_audio_chunk(self, event: dict) -> list[dict]:
        data = str(event.get("data", ""))
        mime_type = str(event.get("mime_type", "audio/webm"))
        if hasattr(self._session, "handle_audio_chunk"):
            return await self._call("handle_audio_chunk", data, mime_type)
        return await self._call("send_audio_chunk", data, mime_type)

    async def _dispatch_audio_stop(self) -> list[dict]:
        if hasattr(self._session, "handle_audio_stop"):
            return await self._call("handle_audio_stop")
        return await self._call("send_audio_stop")

    async def _call(self, method_name: str, *args: Any) -> list[dict]:
        method = getattr(self._session, method_name, None)
        if method is None:
            return [{"type": "realtime.error", "message": f"Session does not support {method_name}."}]
        result = method(*args)
        return await self._resolve(result)

    async def _resolve(self, result: list[dict] | Awaitable[list[dict] | None] | None) -> list[dict]:
        if inspect.isawaitable(result):
            result = await result
        return result or []
