from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.config import get_settings
from app.main import create_app
from app.storage import JsonStorage


def test_ability_tree_get_builds_type_and_question_layers(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("TEXT_MODE", "local")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "demo"}
    storage = JsonStorage(tmp_path)
    storage.write_ability_tree(
        "demo",
        {
            "user_id": "demo",
            "skills": ["机械臂运动控制"],
            "projects": [],
            "evidence": ["iv_1:motion", "iv_2:motion"],
            "target_skills": [],
            "edges": [],
            "evidence_details": [
                {"evidence_id": "iv_1:motion", "interview_id": "iv_1", "skill": "机械臂运动控制", "question": "请介绍项目。", "answer": "回答一", "knowledge_points": []},
                {"evidence_id": "iv_2:motion", "interview_id": "iv_2", "skill": "机械臂运动控制", "question": "请介绍项目", "answer": "回答二", "knowledge_points": []},
            ],
        },
    )

    response = TestClient(app).get("/api/ability-trees/demo")

    assert response.status_code == 200
    data = response.json()
    assert len(data["type_branches"]) == 1
    assert len(data["question_groups"]) == 1
    assert data["question_groups"][0]["evidence_ids"] == ["iv_1:motion", "iv_2:motion"]
    assert data["obsidian_uri"].startswith("obsidian://open?path=")


def test_ability_tree_organize_persists_fallback_and_markdown(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("TEXT_MODE", "local")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "demo"}
    JsonStorage(tmp_path).write_ability_tree(
        "demo",
        {
            "user_id": "demo",
            "skills": [],
            "projects": [],
            "evidence": [],
            "target_skills": [],
            "edges": [],
            "evidence_details": [],
        },
    )

    response = TestClient(app).post("/api/ability-trees/demo/organize")

    assert response.status_code == 200
    assert response.json()["organization_mode"] == "deterministic_fallback"
    assert (tmp_path / "ability_graphs" / "demo" / "index.md").exists()
