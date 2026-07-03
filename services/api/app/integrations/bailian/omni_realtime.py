from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import websockets

from app.integrations.bailian.text_client import BailianTextClient, BailianTextConfig
from app.interviewer_persona import InterviewContext, LocalTextInterviewer, build_interviewer_system_prompt


WebSocketConnect = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class BailianRealtimeConfig:
    api_key: str | None
    model: str
    url: str
    text_mode: str = "local"
    text_model: str = "qwen3.6-plus"
    text_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    candidate_name: str = "豆瓣酱"
    target_role: str = "机械臂运控算法工程师"
    resume_projects: tuple[str, ...] = ("ROS2 机械臂运动控制",)
    resume_skills: tuple[str, ...] = ("ROS2", "机械臂运动控制", "轨迹规划", "插值算法")


class BailianRealtimeAdapter:
    def __init__(
        self,
        config: BailianRealtimeConfig,
        websocket_connect: WebSocketConnect | None = None,
        text_client: BailianTextClient | None = None,
    ):
        self.config = config
        self.websocket_connect = websocket_connect or websockets.connect
        self.websocket: Any | None = None
        self.context = InterviewContext(
            candidate_name=config.candidate_name,
            target_role=config.target_role,
            resume_projects=config.resume_projects,
            resume_skills=config.resume_skills,
        )
        self.system_prompt = build_interviewer_system_prompt(
            candidate_name=config.candidate_name,
            target_role=config.target_role,
        )
        self.text_interviewer = LocalTextInterviewer(self.context)
        self._text_client = text_client or self._create_text_client()

    def validate_ready(self) -> None:
        if not self.config.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is required for Bailian live realtime mode.")
        if not self.config.model:
            raise RuntimeError("Bailian realtime model is required.")
        if not self.config.url.startswith("wss://"):
            raise RuntimeError("Bailian realtime URL must start with wss://.")

    async def connect(self) -> None:
        self.validate_ready()
        self.websocket = await self.websocket_connect(
            self._api_url(),
            additional_headers={"Authorization": f"Bearer {self.config.api_key}"},
        )
        await self._send(
            {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "voice": "Tina",
                    "input_audio_format": "pcm",
                    "output_audio_format": "pcm",
                    "input_audio_transcription": {
                        "model": "qwen3-asr-flash-realtime",
                    },
                    "instructions": self.system_prompt,
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "silence_duration_ms": 800,
                    },
                    "temperature": 0.7,
                },
            }
        )

    def start_events(self) -> list[dict]:
        return [
            {"type": "session.ready", "mode": "bailian"},
            {"type": "assistant.text.delta", "text": self.text_interviewer.initial_question()},
        ]

    async def handle_text(self, text: str) -> list[dict]:
        if self._text_client:
            try:
                self._text_client.add_to_history("user", text)
                reply = await self._text_client.next_question()
                return [
                    {"type": "transcript.item", "speaker": "candidate", "text": text},
                    {"type": "assistant.text.delta", "text": reply},
                    {"type": "text.mode", "mode": "bailian_text", "model": self.config.text_model},
                ]
            except Exception as exc:
                reply = self.text_interviewer.next_question(text)
                return [
                    {"type": "transcript.item", "speaker": "candidate", "text": text},
                    {"type": "realtime.error", "message": f"Bailian text call failed: {exc}"},
                    {"type": "assistant.text.delta", "text": reply},
                    {"type": "text.mode", "mode": "local-fallback"},
                ]

        reply = self.text_interviewer.next_question(text)
        return [
            {"type": "transcript.item", "speaker": "candidate", "text": text},
            {"type": "assistant.text.delta", "text": reply},
            {"type": "text.mode", "mode": "local-low-cost"},
        ]

    async def handle_session_end(self) -> list[dict]:
        return [{"type": "session.ended", "mode": "bailian"}]

    async def send_audio_start(self, mime_type: str, sample_rate: int | None) -> list[dict]:
        if not self._is_supported_pcm(mime_type, sample_rate):
            return [
                {
                    "type": "realtime.error",
                    "message": (
                        "Bailian Qwen-Omni-Realtime requires 16 kHz PCM audio. "
                        f"Current browser stream is {mime_type} at {sample_rate or 'unknown'} Hz."
                    ),
                }
            ]
        return [{"type": "audio.started", "mode": "bailian", "mime_type": mime_type, "sample_rate": sample_rate}]

    async def send_audio_chunk(self, data_base64: str, mime_type: str) -> list[dict]:
        if not self.websocket:
            return [{"type": "realtime.error", "message": "Bailian realtime WebSocket is not connected."}]
        if not self._is_pcm_mime(mime_type):
            return [
                {
                    "type": "realtime.error",
                    "message": "Bailian realtime audio chunks must be base64-encoded 16 kHz PCM.",
                }
            ]
        await self._send({"type": "input_audio_buffer.append", "audio": data_base64})
        return []

    async def send_audio_stop(self) -> list[dict]:
        return [{"type": "audio.stopped", "mode": "bailian"}]

    async def receive_events(self) -> list[dict]:
        if not self.websocket:
            return [{"type": "realtime.error", "message": "Bailian realtime WebSocket is not connected."}]
        message = await self.websocket.recv()
        return self.map_server_event(json.loads(message))

    def map_server_event(self, event: dict) -> list[dict]:
        event_type = event.get("type")
        if event_type == "response.audio_transcript.delta":
            return [{"type": "assistant.text.delta", "text": event.get("delta", "")}]
        if event_type == "response.audio.delta":
            return [
                {
                    "type": "assistant.audio.chunk",
                    "mime_type": "audio/pcm",
                    "sample_rate": 24000,
                    "data": event.get("delta", ""),
                }
            ]
        if event_type == "conversation.item.input_audio_transcription.delta":
            return [
                {
                    "type": "transcript.partial",
                    "speaker": "candidate",
                    "text": f"{event.get('text', '')}{event.get('stash', '')}",
                }
            ]
        if event_type == "conversation.item.input_audio_transcription.completed":
            return [{"type": "transcript.item", "speaker": "candidate", "text": event.get("transcript", "")}]
        if event_type == "session.finished":
            return [{"type": "session.ended", "mode": "bailian"}]
        if event_type == "error":
            error = event.get("error") or {}
            return [{"type": "realtime.error", "message": error.get("message", "Bailian realtime error.")}]
        if event_type in {
            "session.created",
            "session.updated",
            "input_audio_buffer.speech_started",
            "input_audio_buffer.speech_stopped",
            "input_audio_buffer.committed",
            "response.created",
            "response.done",
        }:
            return [{"type": "bailian.event", "event": event_type}]
        return []

    async def close(self) -> None:
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

    async def _send(self, payload: dict) -> None:
        if not self.websocket:
            raise RuntimeError("Bailian realtime WebSocket is not connected.")
        await self.websocket.send(json.dumps(payload, ensure_ascii=False))

    def _api_url(self) -> str:
        parsed = urlsplit(self.config.url)
        query = dict(parse_qsl(parsed.query))
        query["model"] = self.config.model
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))

    def _create_text_client(self) -> BailianTextClient | None:
        if self.config.text_mode != "bailian_text":
            return None
        return BailianTextClient(
            BailianTextConfig(
                api_key=self.config.api_key,
                model=self.config.text_model,
                base_url=self.config.text_base_url,
            ),
            system_prompt=self._text_system_prompt(),
        )

    def _text_system_prompt(self) -> str:
        project_context = "；".join(self.context.resume_projects[:5]) or "暂无项目摘要"
        skill_context = "、".join(self.context.resume_skills[:12]) or "暂无技能摘要"
        return (
            f"{self.system_prompt}\n\n"
            f"候选人技能摘要：{skill_context}\n"
            f"候选人项目摘要：{project_context}\n"
            "你正在进行文字模拟面试。候选人每次回答后，只输出下一句面试追问。"
        )

    def _is_supported_pcm(self, mime_type: str, sample_rate: int | None) -> bool:
        return self._is_pcm_mime(mime_type) and sample_rate == 16000

    def _is_pcm_mime(self, mime_type: str) -> bool:
        normalized = mime_type.lower()
        return normalized in {"audio/pcm", "audio/pcm16", "audio/l16", "pcm"}
