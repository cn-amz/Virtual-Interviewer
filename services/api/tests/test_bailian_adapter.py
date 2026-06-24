import pytest

from app.integrations.bailian.omni_realtime import BailianRealtimeAdapter, BailianRealtimeConfig


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


@pytest.mark.asyncio
async def test_connect_raises_not_implemented_with_valid_config():
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com")
    )
    adapter.validate_ready()

    with pytest.raises(NotImplementedError, match="protocol mapping"):
        await adapter.connect()


@pytest.mark.asyncio
async def test_connect_raises_runtime_error_without_api_key():
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key=None, model="qwen3.5-omni-plus-realtime", url="wss://example.com")
    )

    with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
        await adapter.connect()


@pytest.mark.asyncio
async def test_send_audio_start_raises_not_implemented():
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com")
    )

    with pytest.raises(NotImplementedError):
        await adapter.send_audio_start("audio/webm", 48000)


@pytest.mark.asyncio
async def test_send_audio_chunk_raises_not_implemented():
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com")
    )

    with pytest.raises(NotImplementedError):
        await adapter.send_audio_chunk("dGVzdA==", "audio/webm")


@pytest.mark.asyncio
async def test_send_audio_stop_raises_not_implemented():
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com")
    )

    with pytest.raises(NotImplementedError):
        await adapter.send_audio_stop()


@pytest.mark.asyncio
async def test_close_does_not_raise():
    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(api_key="sk-test", model="qwen3.5-omni-plus-realtime", url="wss://example.com")
    )

    await adapter.close()
