from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    return TestClient(create_app())


def _login(client: TestClient) -> str:
    response = client.post("/api/auth/login", json={"username": "demo", "password": "demo123456"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_login_demo_user_returns_token_and_user(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/auth/login", json={"username": "demo", "password": "demo123456"})

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0
    assert data["user"] == {
        "user_id": "demo",
        "username": "demo",
        "display_name": "演示用户",
    }


def test_me_returns_user_for_bearer_token(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    token = _login(client)

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "demo",
        "username": "demo",
        "display_name": "演示用户",
    }


def test_me_rejects_missing_token(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_rejects_invalid_token(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})

    assert response.status_code == 401


def test_logout_invalidates_token(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    token = _login(client)

    logout_response = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert logout_response.status_code == 200
    assert logout_response.json() == {"status": "ok"}
    assert me_response.status_code == 401


def test_login_rejects_bad_password(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/auth/login", json={"username": "demo", "password": "wrong"})

    assert response.status_code == 401


def test_login_rejects_unknown_user(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})

    assert response.status_code == 401
