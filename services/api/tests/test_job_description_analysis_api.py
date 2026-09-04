from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.config import get_settings
from app.main import create_app


def test_job_description_analysis_endpoint_persists_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("TEXT_MODE", "local")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "demo"}
    client = TestClient(app)
    client.post(
        "/api/job-descriptions/text",
        json={"title": "机械臂岗位", "content": "负责 MoveIt2、逆运动学和手眼标定"},
    )

    response = client.post("/api/job-descriptions/机械臂岗位/analyze")
    listed = client.get("/api/job-descriptions")

    assert response.status_code == 200
    assert response.json()["role_direction"] == "机械臂规划、控制与操作"
    assert response.json()["analysis_mode"] == "deterministic_fallback"
    assert listed.json()[0]["analysis_ready"] is True
