from uuid import uuid4

from app.interview_state import InterviewState
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
            {"type": "session.ready", "session_id": self.session_id},
            {
                "type": "assistant.text.delta",
                "text": "你好，我是你的虚拟面试官。我们先从一段简短自我介绍开始。",
            },
        ]

    def handle_text(self, text: str) -> list[dict]:
        self.transcript.append({"speaker": "candidate", "text": text})
        tool_result = self.tool_router.call("retrieve_profile_context", {"query": text})
        self.state.record_answer_score(3.5)
        action = self.state.next_action()
        self.state.advance_if_ready()
        reply = "我会结合你的项目继续追问。请具体说明你在机械臂运动控制中改了什么、为什么这样改、效果如何。"
        self.transcript.append({"speaker": "assistant", "text": reply})
        return [
            {"type": "transcript.item", "speaker": "candidate", "text": text},
            {"type": "tool.call", "name": tool_result.name, "arguments": {"query": text}},
            {"type": "tool.result", "name": tool_result.name, "summary": tool_result.summary},
            {"type": "interview.action", "action": action, "stage": self.state.stage},
            {"type": "assistant.text.delta", "text": reply},
        ]
