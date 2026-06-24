import base64

import pytest

from app.realtime import MockRealtimeSession
from app.realtime_gateway import RealtimeGateway


@pytest.mark.asyncio
async def test_gateway_start_events():
    session = MockRealtimeSession("profile-a", "jd-1")
    gateway = RealtimeGateway(session)

    events = await gateway.start_events()

    assert events[0]["type"] == "session.ready"
    assert events[1]["type"] == "assistant.text.delta"


@pytest.mark.asyncio
async def test_gateway_text_input_dispatches():
    session = MockRealtimeSession("profile-a", "jd-1")
    gateway = RealtimeGateway(session)

    events = await gateway.dispatch({"type": "text.input", "text": "hello"})

    assert any(e["type"] == "assistant.text.delta" for e in events)
    assert any(e["type"] == "transcript.item" for e in events)


@pytest.mark.asyncio
async def test_gateway_audio_start():
    session = MockRealtimeSession("profile-a", "jd-1")
    gateway = RealtimeGateway(session)

    events = await gateway.dispatch(
        {"type": "audio.start", "mime_type": "audio/webm", "sample_rate": 48000}
    )

    assert events[0]["type"] == "audio.started"
    assert events[0]["mode"] == "mock"


@pytest.mark.asyncio
async def test_gateway_audio_chunk_valid_base64():
    session = MockRealtimeSession("profile-a", "jd-1")
    gateway = RealtimeGateway(session)

    data = base64.b64encode(b"fake audio bytes").decode()
    events = await gateway.dispatch(
        {"type": "audio.chunk", "data": data, "mime_type": "audio/webm"}
    )

    assert events[0]["type"] == "audio.received"
    assert events[0]["bytes"] == 16
    assert events[0]["mode"] == "mock"


@pytest.mark.asyncio
async def test_gateway_audio_chunk_invalid_base64():
    session = MockRealtimeSession("profile-a", "jd-1")
    gateway = RealtimeGateway(session)

    events = await gateway.dispatch(
        {"type": "audio.chunk", "data": "!!!not-valid-base64!!!"}
    )

    assert events[0]["type"] == "audio.error"
    assert events[0]["mode"] == "mock"


@pytest.mark.asyncio
async def test_gateway_audio_stop():
    session = MockRealtimeSession("profile-a", "jd-1")
    gateway = RealtimeGateway(session)

    events = await gateway.dispatch({"type": "audio.stop"})

    assert events[0]["type"] == "audio.stopped"
    assert events[0]["mode"] == "mock"


@pytest.mark.asyncio
async def test_gateway_session_end():
    session = MockRealtimeSession("profile-a", "jd-1")
    gateway = RealtimeGateway(session)

    events = await gateway.dispatch({"type": "session.end"})

    assert events[0]["type"] == "session.ended"
    assert events[0]["session_id"] == session.session_id


@pytest.mark.asyncio
async def test_gateway_unknown_event_type_returns_empty():
    session = MockRealtimeSession("profile-a", "jd-1")
    gateway = RealtimeGateway(session)

    events = await gateway.dispatch({"type": "unknown.event"})

    assert events == []
