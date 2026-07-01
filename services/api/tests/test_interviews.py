from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def test_create_mock_report_returns_report_and_tree():
    client = TestClient(create_app())

    response = client.post("/api/interviews/mock-report")

    assert response.status_code == 200
    payload = response.json()
    assert payload["interview_id"].startswith("int_")
    assert payload["report"]["user_id"] == "豆瓣酱"
    assert payload["ability_tree"]["user_id"] == "豆瓣酱"
    assert payload["report"]["summary"] == "本次面试完成了机械臂运控方向的模拟问答。"


def test_create_mock_report_uses_authenticated_user(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "demo", "password": "demo123456"})
    token = login.json()["access_token"]

    response = client.post("/api/interviews/mock-report", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["report"]["user_id"] == "demo"
    assert payload["ability_tree"]["user_id"] == "demo"


def test_create_mock_report_rejects_invalid_token():
    client = TestClient(create_app())

    response = client.post("/api/interviews/mock-report", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401


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


def test_bailian_text_mode_continues_when_realtime_connect_fails(monkeypatch):
    from app.routers import interviews

    class BrokenRealtimeTextSession:
        async def connect(self):
            raise RuntimeError("realtime unavailable")

        def start_events(self):
            return [{"type": "session.ready", "mode": "bailian"}]

        async def handle_text(self, text: str):
            return [
                {"type": "transcript.item", "speaker": "candidate", "text": text},
                {"type": "assistant.text.delta", "text": "你本人负责哪个模块？"},
                {"type": "text.mode", "mode": "bailian_text", "model": "qwen3.6-plus"},
            ]

        async def close(self):
            return None

    monkeypatch.setenv("REALTIME_MODE", "bailian")
    monkeypatch.setenv("TEXT_MODE", "bailian_text")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test")
    get_settings.cache_clear()
    monkeypatch.setattr(interviews, "create_realtime_session", lambda settings: BrokenRealtimeTextSession())
    client = TestClient(create_app())

    with client.websocket_connect("/api/interviews/realtime") as websocket:
        error = websocket.receive_json()
        ready = websocket.receive_json()
        websocket.send_json({"type": "text.input", "text": "我负责 ROS2 运动控制。"})
        transcript = websocket.receive_json()
        reply = websocket.receive_json()
        mode = websocket.receive_json()

    assert error["type"] == "realtime.error"
    assert ready == {"type": "session.ready", "mode": "bailian"}
    assert transcript["type"] == "transcript.item"
    assert reply == {"type": "assistant.text.delta", "text": "你本人负责哪个模块？"}
    assert mode == {"type": "text.mode", "mode": "bailian_text", "model": "qwen3.6-plus"}
