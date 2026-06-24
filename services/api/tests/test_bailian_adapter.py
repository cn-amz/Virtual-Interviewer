import pytest

from app.integrations.bailian.omni_realtime import BailianRealtimeAdapter, BailianRealtimeConfig


class FakeRealtimeSocket:
    def __init__(self):
        self.sent: list[dict] = []
        self.closed = False
        self.incoming: list[str] = []

    async def send(self, payload: str):
        import json

        self.sent.append(json.loads(payload))

    async def close(self):
        self.closed = True

    async def recv(self):
        if not self.incoming:
            raise RuntimeError("no incoming events")
        return self.incoming.pop(0)


class FakeWebSocketFactory:
    def __init__(self):
        self.socket = FakeRealtimeSocket()
        self.url = ""
        self.additional_headers: dict[str, str] = {}

    async def __call__(self, url: str, additional_headers: dict[str, str]):
        self.url = url
        self.additional_headers = additional_headers
        return self.socket


def test_adapter_requires_api_key():
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key=None, model="qwen3.5-omni-plus-realtime", url="wss://example.com")
    )

    with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
        adapter.validate_ready()


def test_adapter_accepts_valid_config():
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com")
    )

    adapter.validate_ready()


def test_adapter_exposes_interviewer_system_prompt():
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com")
    )

    assert "技术面试官" in adapter.system_prompt
    assert "不是通用AI助手" in adapter.system_prompt


def test_adapter_maps_bailian_server_events():
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com")
    )

    assert adapter.map_server_event({"type": "response.audio_transcript.delta", "delta": "继续说"}) == [
        {"type": "assistant.text.delta", "text": "继续说"}
    ]
    assert adapter.map_server_event({"type": "response.audio.delta", "delta": "AAAA"}) == [
        {"type": "assistant.audio.chunk", "mime_type": "audio/pcm", "data": "AAAA"}
    ]
    assert adapter.map_server_event(
        {"type": "conversation.item.input_audio_transcription.completed", "transcript": "我的项目是..."}
    ) == [{"type": "transcript.item", "speaker": "candidate", "text": "我的项目是..."}]
    assert adapter.map_server_event({"type": "error", "error": {"message": "bad request"}}) == [
        {"type": "realtime.error", "message": "bad request"}
    ]


@pytest.mark.asyncio
async def test_receive_events_reads_and_maps_one_server_event():
    factory = FakeWebSocketFactory()
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com"),
        websocket_connect=factory,
    )
    await adapter.connect()
    factory.socket.incoming.append('{"type":"response.audio_transcript.delta","delta":"追问"}')

    events = await adapter.receive_events()

    assert events == [{"type": "assistant.text.delta", "text": "追问"}]


@pytest.mark.asyncio
async def test_connect_opens_websocket_and_updates_session():
    factory = FakeWebSocketFactory()
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com"),
        websocket_connect=factory,
    )

    await adapter.connect()

    assert factory.url == "wss://example.com?model=qwen3.5-omni-plus-realtime"
    assert factory.additional_headers == {"Authorization": "Bearer sk-test"}
    assert factory.socket.sent[0]["type"] == "session.update"
    assert factory.socket.sent[0]["session"]["input_audio_format"] == "pcm"
    assert "技术面试官" in factory.socket.sent[0]["session"]["instructions"]


@pytest.mark.asyncio
async def test_connect_raises_runtime_error_without_api_key():
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key=None, model="qwen3.5-omni-plus-realtime", url="wss://example.com")
    )

    with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
        await adapter.connect()


@pytest.mark.asyncio
async def test_send_audio_start_raises_not_implemented():
    factory = FakeWebSocketFactory()
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com"),
        websocket_connect=factory,
    )
    await adapter.connect()

    events = await adapter.send_audio_start("audio/webm", 48000)

    assert events[0]["type"] == "realtime.error"
    assert "16 kHz PCM" in events[0]["message"]


@pytest.mark.asyncio
async def test_send_audio_start_accepts_pcm16():
    factory = FakeWebSocketFactory()
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com"),
        websocket_connect=factory,
    )
    await adapter.connect()

    events = await adapter.send_audio_start("audio/pcm", 16000)

    assert events == [{"type": "audio.started", "mode": "bailian", "mime_type": "audio/pcm", "sample_rate": 16000}]


@pytest.mark.asyncio
async def test_text_input_uses_local_low_cost_interviewer_path():
    factory = FakeWebSocketFactory()
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com"),
        websocket_connect=factory,
    )
    await adapter.connect()

    events = await adapter.handle_text("我通过ROS2完成机械臂运动控制。")

    assert any(event["type"] == "transcript.item" and event["speaker"] == "candidate" for event in events)
    assert any(event["type"] == "assistant.text.delta" for event in events)
    assert any(event == {"type": "text.mode", "mode": "local-low-cost"} for event in events)
    assert len(factory.socket.sent) == 1


@pytest.mark.asyncio
async def test_send_audio_chunk_raises_not_implemented():
    factory = FakeWebSocketFactory()
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com"),
        websocket_connect=factory,
    )
    await adapter.connect()

    events = await adapter.send_audio_chunk("dGVzdA==", "audio/pcm")

    assert events == []
    assert factory.socket.sent[-1] == {"type": "input_audio_buffer.append", "audio": "dGVzdA=="}


@pytest.mark.asyncio
async def test_send_audio_stop_raises_not_implemented():
    factory = FakeWebSocketFactory()
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com"),
        websocket_connect=factory,
    )
    await adapter.connect()

    events = await adapter.send_audio_stop()

    assert events == []
    assert factory.socket.sent[-1] == {"type": "session.finish"}


@pytest.mark.asyncio
async def test_close_does_not_raise():
    factory = FakeWebSocketFactory()
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com"),
        websocket_connect=factory,
    )
    await adapter.connect()

    await adapter.close()

    assert factory.socket.closed is True
