import array
import base64
import json

import pytest

from app.integrations.minicpm.realtime import MiniCPMRealtimeAdapter, MiniCPMRealtimeConfig


class FakeRealtimeSocket:
    def __init__(self, incoming: list[dict]):
        self.incoming = [json.dumps(message) for message in incoming]
        self.sent: list[dict] = []
        self.closed = False

    async def recv(self) -> str:
        return self.incoming.pop(0)

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def close(self) -> None:
        self.closed = True


class FakeWebSocketFactory:
    def __init__(self, incoming: list[dict]):
        self.socket = FakeRealtimeSocket(incoming)
        self.url = ""
        self.kwargs: dict = {}

    async def __call__(self, url: str, **kwargs):
        self.url = url
        self.kwargs = kwargs
        return self.socket


def float32_base64(samples: list[float]) -> str:
    values = array.array("f", samples)
    return base64.b64encode(values.tobytes()).decode()


def test_adapter_requires_secure_websocket_url():
    adapter = MiniCPMRealtimeAdapter(MiniCPMRealtimeConfig(url="http://127.0.0.1:8006"))

    with pytest.raises(RuntimeError, match="wss://"):
        adapter.validate_ready()


@pytest.mark.asyncio
async def test_connect_prepares_an_audio_duplex_session():
    factory = FakeWebSocketFactory([{"type": "queue_done"}, {"type": "prepared"}])
    adapter = MiniCPMRealtimeAdapter(
        MiniCPMRealtimeConfig(url="wss://127.0.0.1:8006"),
        websocket_connect=factory,
    )

    await adapter.connect()

    assert factory.url.startswith("wss://127.0.0.1:8006/ws/duplex/adx_")
    assert factory.kwargs["proxy"] is None
    assert factory.socket.sent[0]["type"] == "prepare"
    assert "技术面试官" in factory.socket.sent[0]["system_prompt"]
    assert adapter.start_events()[0]["mode"] == "minicpm"


@pytest.mark.asyncio
async def test_connect_sends_compact_interviewer_context_that_resists_reverse_questions():
    factory = FakeWebSocketFactory([{"type": "queue_done"}, {"type": "prepared"}])
    adapter = MiniCPMRealtimeAdapter(
        MiniCPMRealtimeConfig(
            url="wss://127.0.0.1:8006",
            candidate_name="测试候选人",
            target_role="机器人算法工程师",
            resume_projects=("机械臂轨迹规划", "ROS2 控制器开发"),
            resume_skills=("ROS2", "MoveIt", "C++"),
            role_direction="机械臂规划与控制",
            interview_focus=("轨迹平滑", "真机稳定性"),
            initial_prompt="优先核验候选人的真实职责。",
            resume_text=("完整简历正文" * 500) + "不应进入提示词的尾部标记",
        ),
        websocket_connect=factory,
    )

    await adapter.connect()

    prompt = factory.socket.sent[0]["system_prompt"]
    assert "测试候选人" in prompt
    assert "机器人算法工程师" in prompt
    assert "机械臂轨迹规划" in prompt
    assert "候选人反问" in prompt
    assert "不得替候选人回答" in prompt
    assert "不应进入提示词的尾部标记" not in prompt
    assert len(prompt) <= 500


@pytest.mark.asyncio
async def test_audio_chunk_converts_pcm16_to_minicpm_float32():
    factory = FakeWebSocketFactory([{"type": "queue_done"}, {"type": "prepared"}])
    adapter = MiniCPMRealtimeAdapter(
        MiniCPMRealtimeConfig(url="wss://127.0.0.1:8006"),
        websocket_connect=factory,
    )
    await adapter.connect()
    pcm16 = base64.b64encode(b"\x00\x80\x00\x40" + b"\x00\x00" * 15998).decode()

    events = await adapter.send_audio_chunk(pcm16, "audio/pcm")

    assert events == []
    audio = base64.b64decode(factory.socket.sent[-1]["audio_base64"])
    samples = array.array("f")
    samples.frombytes(audio)
    assert list(samples[:2]) == pytest.approx([-1.0, 0.5])
    assert len(samples) == 16000


def test_result_maps_float32_audio_to_frontend_pcm16_without_a_false_turn_boundary():
    adapter = MiniCPMRealtimeAdapter(MiniCPMRealtimeConfig(url="wss://127.0.0.1:8006"))

    events = adapter.map_server_event(
        {
            "type": "result",
            "is_listen": False,
            "text": "请具体说明。",
            "audio_data": float32_base64([-1.0, 0.5]),
            "end_of_turn": True,
        }
    )

    assert events[0] == {
        "type": "assistant.text.delta",
        "text": "请具体说明。",
        "turn_id": "local-assistant-1",
        "is_final": False,
        "source": "provider",
    }
    assert events[1]["type"] == "assistant.audio.chunk"
    assert events[1]["mime_type"] == "audio/pcm"
    assert events[1]["sample_rate"] == 24000
    assert base64.b64decode(events[1]["data"]) == b"\x00\x80\xff\x3f"
    assert len(events) == 2


def test_audio_only_maps_upstream_wav_poll_audio_to_frontend_pcm16():
    adapter = MiniCPMRealtimeAdapter(MiniCPMRealtimeConfig(url="wss://127.0.0.1:8006"))

    events = adapter.map_server_event({"type": "audio_only", "audio_data": float32_base64([-1.0, 0.5])})

    assert events == [
        {
            "type": "assistant.audio.chunk",
            "mime_type": "audio/pcm",
            "sample_rate": 24000,
            "data": base64.b64encode(b"\x00\x80\xff\x3f").decode(),
            "turn_id": "local-assistant-1",
            "is_final": False,
            "source": "provider",
        }
    ]


def test_minicpm_reuses_one_assistant_turn_until_it_listens_again():
    adapter = MiniCPMRealtimeAdapter(MiniCPMRealtimeConfig(url="wss://127.0.0.1:8006"))

    first = adapter.map_server_event({"type": "result", "is_listen": False, "text": "第一段"})
    second = adapter.map_server_event({"type": "result", "is_listen": False, "text": "第二段"})
    adapter.map_server_event({"type": "result", "is_listen": True})
    third = adapter.map_server_event({"type": "result", "is_listen": False, "text": "下一轮"})

    assert first[0]["turn_id"] == "local-assistant-1"
    assert second[0]["turn_id"] == "local-assistant-1"
    assert third[0]["turn_id"] == "local-assistant-2"


def test_listening_result_does_not_complete_an_assistant_turn():
    adapter = MiniCPMRealtimeAdapter(MiniCPMRealtimeConfig(url="wss://127.0.0.1:8006"))

    assert adapter.map_server_event({"type": "result", "is_listen": True, "end_of_turn": True}) == []


@pytest.mark.asyncio
async def test_audio_chunks_are_buffered_to_one_second_before_sending_upstream():
    factory = FakeWebSocketFactory([{"type": "queue_done"}, {"type": "prepared"}])
    adapter = MiniCPMRealtimeAdapter(
        MiniCPMRealtimeConfig(url="wss://127.0.0.1:8006"),
        websocket_connect=factory,
    )
    await adapter.connect()
    half_second = base64.b64encode(b"\x00\x00" * 8000).decode()

    assert await adapter.send_audio_chunk(half_second, "audio/pcm") == []
    assert [message["type"] for message in factory.socket.sent] == ["prepare"]

    assert await adapter.send_audio_chunk(half_second, "audio/pcm") == []
    payload = factory.socket.sent[-1]
    assert payload["type"] == "audio_chunk"
    assert len(base64.b64decode(payload["audio_base64"])) == 16000 * 4


@pytest.mark.asyncio
async def test_audio_stop_flushes_a_partial_second_with_silence_padding():
    factory = FakeWebSocketFactory([{"type": "queue_done"}, {"type": "prepared"}])
    adapter = MiniCPMRealtimeAdapter(
        MiniCPMRealtimeConfig(url="wss://127.0.0.1:8006"),
        websocket_connect=factory,
    )
    await adapter.connect()
    half_second = base64.b64encode(b"\x00\x00" * 8000).decode()

    await adapter.send_audio_chunk(half_second, "audio/pcm")
    events = await adapter.send_audio_stop()

    assert factory.socket.sent[-1]["type"] == "audio_chunk"
    assert len(base64.b64decode(factory.socket.sent[-1]["audio_base64"])) == 16000 * 4
    assert events == [{"type": "audio.stopped", "mode": "minicpm"}]


@pytest.mark.asyncio
async def test_audio_chunks_wait_for_each_upstream_result_before_sending_the_next_chunk():
    factory = FakeWebSocketFactory(
        [
            {"type": "queue_done"},
            {"type": "prepared"},
            {"type": "result", "is_listen": False, "end_of_turn": True},
        ]
    )
    adapter = MiniCPMRealtimeAdapter(
        MiniCPMRealtimeConfig(url="wss://127.0.0.1:8006"),
        websocket_connect=factory,
    )
    await adapter.connect()
    second = base64.b64encode(b"\x00\x00" * 16000).decode()

    await adapter.send_audio_chunk(second, "audio/pcm")
    await adapter.send_audio_chunk(second, "audio/pcm")
    await adapter.send_audio_chunk(second, "audio/pcm")
    assert [message["type"] for message in factory.socket.sent] == ["prepare", "audio_chunk"]

    assert await adapter.receive_events() == []
    assert [message["type"] for message in factory.socket.sent] == ["prepare", "audio_chunk", "audio_chunk"]


@pytest.mark.asyncio
async def test_audio_stop_queues_two_seconds_of_silence_for_minicpm_turn_detection():
    factory = FakeWebSocketFactory(
        [
            {"type": "queue_done"},
            {"type": "prepared"},
            {"type": "result", "is_listen": True},
        ]
    )
    adapter = MiniCPMRealtimeAdapter(
        MiniCPMRealtimeConfig(url="wss://127.0.0.1:8006"),
        websocket_connect=factory,
    )
    await adapter.connect()
    second = base64.b64encode(b"\x01\x00" * 16000).decode()

    await adapter.send_audio_chunk(second, "audio/pcm")
    await adapter.send_audio_stop()
    await adapter.receive_events()

    silence = array.array("f")
    silence.frombytes(base64.b64decode(factory.socket.sent[-1]["audio_base64"]))
    assert len(silence) == 16000
    assert not any(silence)
