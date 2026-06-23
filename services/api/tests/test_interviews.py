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
