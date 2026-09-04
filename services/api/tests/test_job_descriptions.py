from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.config import get_settings
from app.main import create_app


def test_create_job_description_from_text(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "demo"}

    response = TestClient(app).post(
        "/api/job-descriptions/text",
        json={"title": "运动控制算法工程师", "content": "## 岗位职责\n\n负责轨迹规划"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "运动控制算法工程师.md"
    assert (tmp_path / "interview_job_descriptions" / "运动控制算法工程师.md").exists()


def test_create_job_description_from_text_rejects_empty_content(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "demo"}

    response = TestClient(app).post(
        "/api/job-descriptions/text",
        json={"title": "岗位", "content": "  "},
    )

    assert response.status_code == 400
