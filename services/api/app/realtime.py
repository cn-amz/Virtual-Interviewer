import base64
import binascii
from uuid import uuid4

from app.interview_state import InterviewState
from app.interviewer_persona import next_mock_interviewer_question
from app.tool_router import create_default_tool_router


class MockRealtimeSession:
    def __init__(self, profile_id: str, jd_id: str):
        self.session_id = f"iv_{uuid4().hex[:10]}"
        self.profile_id = profile_id
        self.jd_id = jd_id
        self.state = InterviewState()
        self.tool_router = create_default_tool_router()
        self.transcript: list[dict[str, str]] = []

    def start_events(self) -> list[dict]:
        return [
            {"type": "session.ready", "session_id": self.session_id, "mode": "mock"},
            {
                "type": "assistant.text.delta",
                "text": next_mock_interviewer_question(self.state.stage, ""),
            },
        ]

    def handle_text(self, text: str) -> list[dict]:
        self.transcript.append({"speaker": "candidate", "text": text})
        tool_result = self.tool_router.call("retrieve_profile_context", {"query": text})
        self.state.record_answer_score(3.5)
        action = self.state.next_action()
        reply = next_mock_interviewer_question(self.state.stage, text)
        self.state.advance_if_ready()
        self.transcript.append({"speaker": "assistant", "text": reply})
        return [
            {"type": "transcript.item", "speaker": "candidate", "text": text},
            {"type": "tool.call", "name": tool_result.name, "arguments": {"query": text}},
            {"type": "tool.result", "name": tool_result.name, "summary": tool_result.summary},
            {"type": "interview.action", "action": action, "stage": self.state.stage},
            {"type": "assistant.text.delta", "text": reply},
        ]

    def handle_audio_start(
        self, mime_type: str = "audio/webm", sample_rate: int | None = None
    ) -> list[dict]:
        return [
            {
                "type": "audio.started",
                "mode": "mock",
                "mime_type": mime_type,
                "sample_rate": sample_rate,
            }
        ]

    def handle_audio_chunk(
        self, data_base64: str, mime_type: str = "audio/webm"
    ) -> list[dict]:
        try:
            raw = base64.b64decode(data_base64, validate=True)
        except (binascii.Error, ValueError):
            return [{"type": "audio.error", "message": "Invalid base64 audio chunk.", "mode": "mock"}]
        return [{"type": "audio.received", "bytes": len(raw), "mode": "mock", "mime_type": mime_type}]

    def handle_audio_stop(self) -> list[dict]:
        return [{"type": "audio.stopped", "mode": "mock"}]

    def handle_session_end(self) -> list[dict]:
        return [{"type": "session.ended", "session_id": self.session_id}]
