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
