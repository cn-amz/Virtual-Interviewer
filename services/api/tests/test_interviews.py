from fastapi.testclient import TestClient

from app.main import create_app


def test_create_mock_report_returns_report_and_tree():
    client = TestClient(create_app())

    response = client.post("/api/interviews/mock-report")

    assert response.status_code == 200
    payload = response.json()
    assert payload["interview_id"].startswith("int_")
    assert payload["report"]["user_id"] == "豆瓣酱"
    assert payload["ability_tree"]["user_id"] == "豆瓣酱"


def test_realtime_websocket_accepts_mock_audio_events():
    client = TestClient(create_app())

    with client.websocket_connect("/api/interviews/realtime") as websocket:
        ready = websocket.receive_json()
        greeting = websocket.receive_json()

        websocket.send_json(
            {"type": "audio.start", "mime_type": "audio/webm;codecs=opus", "sample_rate": 48000}
        )
        started = websocket.receive_json()

        websocket.send_json({"type": "audio.chunk", "mime_type": "audio/webm;codecs=opus", "data": "dGVzdA=="})
        received = websocket.receive_json()

        websocket.send_json({"type": "audio.stop"})
        stopped = websocket.receive_json()

        websocket.send_json({"type": "session.end"})
        ended = websocket.receive_json()

    assert ready["type"] == "session.ready"
    assert greeting["type"] == "assistant.text.delta"
    assert started == {
        "type": "audio.started",
        "mode": "mock",
        "mime_type": "audio/webm;codecs=opus",
        "sample_rate": 48000,
    }
    assert received["type"] == "audio.received"
    assert received["bytes"] == 4
    assert stopped == {"type": "audio.stopped", "mode": "mock"}
    assert ended["type"] == "session.ended"
