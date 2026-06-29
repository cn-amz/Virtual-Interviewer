from unittest.mock import MagicMock

import pytest

from app.integrations.bailian.text_client import BailianTextClient, BailianTextConfig


def _fake_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    return resp


@pytest.mark.asyncio
async def test_text_client_raises_without_api_key():
    client = BailianTextClient(BailianTextConfig(api_key=None), system_prompt="测试")

    with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
        await client.next_question()


@pytest.mark.asyncio
async def test_text_client_posts_to_chat_completions():
    async def fake_post(url, **kwargs):
        assert url.endswith("/chat/completions")
        assert kwargs["headers"]["Authorization"] == "Bearer sk-test"
        assert kwargs["json"]["model"] == "qwen3.6plus"
        messages = kwargs["json"]["messages"]
        assert messages[0] == {"role": "system", "content": "你是技术面试官。"}
        assert messages[1] == {"role": "user", "content": "我做 ROS 项目。"}
        return _fake_response("你负责哪个模块？")

    client = BailianTextClient(
        BailianTextConfig(api_key="sk-test"),
        system_prompt="你是技术面试官。",
        http_post=fake_post,
    )
    client.add_to_history("user", "我做 ROS 项目。")

    reply = await client.next_question()

    assert reply == "你负责哪个模块？"


@pytest.mark.asyncio
async def test_text_client_tracks_history():
    client = BailianTextClient(BailianTextConfig(api_key="sk-test"), system_prompt="测试")
    client.add_to_history("user", "第一条消息")

    assert client.history == [{"role": "user", "content": "第一条消息"}]


@pytest.mark.asyncio
async def test_text_client_appends_assistant_reply_to_history():
    async def fake_post(url, **kwargs):
        return _fake_response("追问细节？")

    client = BailianTextClient(
        BailianTextConfig(api_key="sk-test"),
        system_prompt="测试",
        http_post=fake_post,
    )
    client.add_to_history("user", "一个问题")

    await client.next_question()

    assert client.history[1] == {"role": "assistant", "content": "追问细节？"}


@pytest.mark.asyncio
async def test_text_client_handles_missing_choices():
    async def fake_post(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"choices": []}
        return resp

    client = BailianTextClient(
        BailianTextConfig(api_key="sk-test"),
        system_prompt="测试",
        http_post=fake_post,
    )
    client.add_to_history("user", "一个问题")

    with pytest.raises(RuntimeError, match="did not contain assistant content"):
        await client.next_question()


@pytest.mark.asyncio
async def test_adapter_handle_text_uses_cloud_when_text_mode_bailian():
    from app.integrations.bailian.omni_realtime import BailianRealtimeAdapter, BailianRealtimeConfig

    async def fake_post(url, **kwargs):
        return _fake_response("这个项目里你本人负责什么？")

    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(
            api_key="sk-test",
            model="qwen3.5-omni-plus-realtime",
            url="wss://example.com",
            text_mode="bailian_text",
        )
    )
    assert adapter._text_client is not None
    adapter._text_client._http_post = fake_post

    events = await adapter.handle_text("我负责 ROS2 运动控制。")

    assert events[0] == {"type": "transcript.item", "speaker": "candidate", "text": "我负责 ROS2 运动控制。"}
    assert events[1] == {"type": "assistant.text.delta", "text": "这个项目里你本人负责什么？"}
    assert events[2] == {"type": "text.mode", "mode": "bailian_text", "model": "qwen3.6plus"}


@pytest.mark.asyncio
async def test_adapter_handle_text_falls_back_to_local_on_cloud_error():
    from app.integrations.bailian.omni_realtime import BailianRealtimeAdapter, BailianRealtimeConfig

    async def fake_post(url, **kwargs):
        raise RuntimeError("connection failed")

    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(
            api_key="sk-test",
            model="qwen3.5-omni-plus-realtime",
            url="wss://example.com",
            text_mode="bailian_text",
        )
    )
    assert adapter._text_client is not None
    adapter._text_client._http_post = fake_post

    events = await adapter.handle_text("我负责 ROS2 运动控制。")

    assert events[1]["type"] == "realtime.error"
    assert events[2]["type"] == "assistant.text.delta"
    assert events[3] == {"type": "text.mode", "mode": "local-fallback"}


@pytest.mark.asyncio
async def test_adapter_handle_text_uses_local_when_text_mode_local():
    from app.integrations.bailian.omni_realtime import BailianRealtimeAdapter, BailianRealtimeConfig

    adapter = BailianRealtimeAdapter(
        BailianRealtimeConfig(
            api_key="sk-test",
            model="qwen3.5-omni-plus-realtime",
            url="wss://example.com",
            text_mode="local",
        )
    )

    events = await adapter.handle_text("我负责 ROS2 运动控制。")

    assert events[2] == {"type": "text.mode", "mode": "local-low-cost"}
