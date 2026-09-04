from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.storage import JsonStorage


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


def test_history_requires_login_and_returns_saved_reports(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    JsonStorage(tmp_path).write_interview(
        "iv_history",
        {
            "report": {
                "user_id": "demo",
                "summary": "历史报告",
                "score": {"average": 88},
                "transcript": [{"speaker": "candidate", "text": "有效回答"}],
            },
            "ability_tree": {"skills": [], "target_skills": []},
        },
    )
    client = TestClient(create_app())
    assert client.get("/api/interviews/history").status_code == 401
    token = client.post(
        "/api/auth/login", json={"username": "demo", "password": "demo123456"}
    ).json()["access_token"]

    response = client.get(
        "/api/interviews/history", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()[0]["report"]["summary"] == "历史报告"


def test_history_hides_mock_and_empty_reports(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    storage = JsonStorage(tmp_path)
    base_report = {"summary": "可展示", "score": {"average": 4}, "transcript": [{"speaker": "candidate", "text": "有效回答"}]}
    storage.write_interview("int_test", {"report": base_report})
    storage.write_interview("iv_empty", {"report": {**base_report, "transcript": []}})
    storage.write_interview("iv_valid", {"report": base_report})

    assert [item["interview_id"] for item in storage.list_interviews()] == ["iv_valid"]


def test_ability_tree_response_includes_obsidian_open_uri(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    JsonStorage(tmp_path).write_ability_tree(
        "demo",
        {"user_id": "demo", "skills": [], "projects": [], "evidence": [], "target_skills": [], "edges": []},
    )
    client = TestClient(create_app())
    token = client.post(
        "/api/auth/login", json={"username": "demo", "password": "demo123456"}
    ).json()["access_token"]

    response = client.get("/api/ability-trees/demo", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["obsidian_uri"].startswith("obsidian://open?path=")
    assert response.json()["markdown_path"].endswith("ability_graphs\\demo\\index.md")


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
        persisted = websocket.receive_json()

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
    assert persisted == {
        "type": "session.persisted",
        "session_id": ready["session_id"],
        "status": "completed",
    }


def test_realtime_persists_transcript_and_audio_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    client = TestClient(create_app())

    with client.websocket_connect("/api/interviews/realtime") as websocket:
        ready = websocket.receive_json()
        websocket.receive_json()
        websocket.send_json({"type": "text.input", "text": "我负责 ROS2 运动控制。"})
        for _ in range(5):
            websocket.receive_json()
        websocket.send_json({"type": "audio.chunk", "data": "dGVzdA==", "mime_type": "audio/pcm"})
        websocket.receive_json()
        websocket.send_json({"type": "session.end"})
        websocket.receive_json()
        persisted = websocket.receive_json()

    payload = JsonStorage(tmp_path).read_interview(ready["session_id"])
    assert persisted == {
        "type": "session.persisted",
        "session_id": ready["session_id"],
        "status": "completed",
    }
    assert payload["status"] == "completed"
    assert {item["speaker"] for item in payload["transcript"]} == {"assistant", "candidate"}
    assert payload["audio_metrics"] == {
        "input_chunks": 1,
        "input_bytes": 4,
        "output_chunks": 0,
        "output_bytes": 0,
    }
    assert not [item for item in payload["events"] if item["event"].get("type") == "audio.chunk"]


def test_realtime_cancel_persists_cancelled_without_report(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    client = TestClient(create_app())

    with client.websocket_connect("/api/interviews/realtime") as websocket:
        ready = websocket.receive_json()
        websocket.receive_json()
        websocket.send_json({"type": "session.cancel"})
        assert websocket.receive_json()["type"] == "session.ended"
        assert websocket.receive_json() == {
            "type": "session.persisted",
            "session_id": ready["session_id"],
            "status": "cancelled",
        }

    payload = JsonStorage(tmp_path).read_interview(ready["session_id"])
    assert payload["status"] == "cancelled"
    assert payload["close_reason"] == "client_session_cancel"
    assert "report" not in payload


def test_analyze_saved_transcript_writes_report_and_tree(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    storage = JsonStorage(tmp_path)
    storage.write_interview(
        "iv_saved",
        {
            "interview_id": "iv_saved",
            "user_id": "demo",
            "transcript": [
                {"speaker": "assistant", "text": "请介绍项目。"},
                {"speaker": "candidate", "text": "我使用 ROS2 完成机械臂运动控制。"},
            ],
            "events": [],
        },
    )
    client = TestClient(create_app())
    token = client.post(
        "/api/auth/login", json={"username": "demo", "password": "demo123456"}
    ).json()["access_token"]

    response = client.post("/api/interviews/iv_saved/analyze", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["report"]["transcript"][1]["text"].startswith("我使用 ROS2")
    assert (tmp_path / "ability_graphs" / "demo" / "index.md").exists()


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
    monkeypatch.setattr(
        interviews,
        "create_realtime_session",
        lambda settings, **_kwargs: BrokenRealtimeTextSession(),
    )
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


def test_create_realtime_session_selects_minicpm_provider(monkeypatch):
    from app.integrations.minicpm.realtime import MiniCPMRealtimeAdapter
    from app.routers.interviews import create_realtime_session

    monkeypatch.setenv("REALTIME_MODE", "minicpm")
    monkeypatch.setenv("MINICPM_REALTIME_URL", "wss://127.0.0.1:8006")
    get_settings.cache_clear()

    session = create_realtime_session(get_settings())

    assert isinstance(session, MiniCPMRealtimeAdapter)
    assert session.config.url == "wss://127.0.0.1:8006"


def test_provider_status_normalizes_minicpm_loading_before_busy():
    from app.routers.interviews import normalize_minicpm_status

    assert normalize_minicpm_status(
        {
            "idle_workers": 1,
            "loading_workers": 1,
            "busy_workers": 1,
            "queue_length": 2,
        }
    ) == {
        "provider": "minicpm",
        "state": "loading",
        "detail": "模型正在加载或重置",
        "queue_length": 2,
    }


def test_provider_status_reports_real_comni_duplex_worker_as_busy():
    from app.routers.interviews import normalize_minicpm_status

    assert normalize_minicpm_status(
        {
            "gateway_healthy": True,
            "total_workers": 1,
            "idle_workers": 0,
            "busy_workers": 0,
            "duplex_workers": 1,
            "loading_workers": 0,
            "error_workers": 0,
            "offline_workers": 0,
            "queue_length": 0,
        }
    ) == {
        "provider": "minicpm",
        "state": "busy",
        "detail": "模型正在处理中",
        "queue_length": 0,
    }


async def test_provider_status_loads_minicpm_idle_from_derived_http_url():
    from app.config import Settings
    from app.routers.interviews import resolve_provider_status

    async def load_status(url: str) -> dict:
        assert url == "https://127.0.0.1:8006/status"
        return {
            "idle_workers": 1,
            "loading_workers": 0,
            "busy_workers": 0,
            "queue_length": 0,
        }

    status = await resolve_provider_status(
        "minicpm",
        Settings(minicpm_realtime_url="wss://127.0.0.1:8006"),
        load_status,
    )

    assert status == {
        "provider": "minicpm",
        "state": "idle",
        "detail": "模型已就绪",
        "queue_length": 0,
    }


def test_provider_status_returns_offline_when_minicpm_is_unreachable(monkeypatch):
    from app.config import Settings
    from app.routers import interviews

    async def unavailable(_url: str) -> dict:
        raise RuntimeError("gateway unavailable")

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        minicpm_realtime_url="wss://127.0.0.1:8006"
    )
    monkeypatch.setattr(interviews, "fetch_minicpm_status", unavailable)

    response = TestClient(app).get("/api/interviews/providers/minicpm/status")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "minicpm",
        "state": "offline",
        "detail": "MiniCPM 服务不可用",
        "queue_length": 0,
    }


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"idle_workers": 1, "queue_length": -1},
        {"idle_workers": "one", "queue_length": "invalid"},
    ],
)
def test_provider_status_route_downgrades_malformed_minicpm_payload(payload, monkeypatch):
    from app.config import Settings
    from app.routers import interviews

    async def load_malformed_status(_url: str):
        return payload

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        minicpm_realtime_url="wss://127.0.0.1:8006"
    )
    monkeypatch.setattr(interviews, "fetch_minicpm_status", load_malformed_status)

    response = TestClient(app).get("/api/interviews/providers/minicpm/status")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "minicpm",
        "state": "offline",
        "detail": "MiniCPM 服务不可用",
        "queue_length": 0,
    }


def test_provider_status_returns_idle_for_configured_bailian():
    from app.config import Settings

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        DASHSCOPE_API_KEY="sk-test"
    )

    response = TestClient(app).get("/api/interviews/providers/bailian/status")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "bailian",
        "state": "idle",
        "detail": "百炼服务已配置",
        "queue_length": 0,
    }


def test_load_interview_context_uses_selected_profile_resume_and_job_description(tmp_path, monkeypatch):
    from app.routers.interviews import load_interview_context

    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    profile_root = tmp_path / "interview_profiles" / "候选人甲"
    profile_root.mkdir(parents=True)
    (profile_root / "profile.json").write_text(
        '{"profile_id":"候选人甲","name":"候选人甲","skills":{"robotics":["ROS2"]},"projects":[]}',
        encoding="utf-8",
    )
    with ZipFile(profile_root / "算法岗位简历.docx", "w") as document:
        document.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>负责机械臂轨迹规划与 ROS2 控制器。</w:t></w:r></w:p></w:body></w:document>',
        )
    jd_root = tmp_path / "interview_job_descriptions"
    jd_root.mkdir()
    (jd_root / "运动规划岗.md").write_text("# 运动规划工程师\n\n负责 MoveIt 与轨迹优化。", encoding="utf-8")

    context = load_interview_context(
        get_settings(),
        profile_id="候选人甲",
        resume_name="算法岗位简历.docx",
        jd_id="运动规划岗",
    )

    assert context["candidate_name"] == "候选人甲"
    assert context["target_role"] == "运动规划工程师"
    assert context["resume_name"] == "算法岗位简历.docx"
    assert "机械臂轨迹规划" in context["resume_text"]
    assert "负责 MoveIt 与轨迹优化" in context["job_description_text"]
    assert context["question_strategy"] == ()


def test_load_interview_context_uses_saved_jd_question_strategy(tmp_path, monkeypatch):
    from app.routers.interviews import load_interview_context

    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    get_settings.cache_clear()
    profile_root = tmp_path / "interview_profiles" / "候选人甲"
    profile_root.mkdir(parents=True)
    (profile_root / "profile.json").write_text(
        '{"profile_id":"候选人甲","name":"候选人甲","skills":{},"projects":[]}',
        encoding="utf-8",
    )
    jd_root = tmp_path / "interview_job_descriptions"
    jd_root.mkdir()
    (jd_root / "多模态岗.md").write_text("# 多模态应用工程师\n\n负责 RAG 评估。", encoding="utf-8")
    (jd_root / "多模态岗.analysis.json").write_text(
        """{
          "jd_id": "多模态岗",
          "title": "多模态应用工程师",
          "role_family": "AI 应用",
          "role_direction": "多模态 RAG",
          "focus_points": ["检索评估"],
          "question_strategy": ["追问召回率与准确率"],
          "initial_prompt": "核验候选人的真实项目证据。",
          "source_keywords": ["RAG"],
          "research_sources": [],
          "analysis_mode": "bailian",
          "analysis_error": null,
          "updated_at": "2026-09-03T00:00:00Z"
        }""",
        encoding="utf-8",
    )

    context = load_interview_context(
        get_settings(),
        profile_id="候选人甲",
        jd_id="多模态岗",
    )

    assert context["question_strategy"] == ("追问召回率与准确率",)


def test_create_bailian_session_passes_jd_grounding_fields():
    from app.config import Settings
    from app.routers.interviews import create_realtime_session

    context = {
        "profile_id": "候选人甲",
        "jd_id": "多模态岗",
        "resume_name": "",
        "candidate_name": "候选人甲",
        "target_role": "多模态应用工程师",
        "resume_projects": (),
        "resume_skills": (),
        "role_direction": "多模态 RAG",
        "interview_focus": ("检索评估",),
        "question_strategy": ("追问召回率与准确率",),
        "initial_prompt": "核验真实证据。",
        "resume_text": "",
        "job_description_text": "负责 RAG 评估与 Agent 工作流。",
    }

    session = create_realtime_session(
        Settings(DASHSCOPE_API_KEY="sk-test"),
        provider="bailian",
        context=context,
    )

    assert session.config.job_description_text == "负责 RAG 评估与 Agent 工作流。"
    assert session.config.question_strategy == ("追问召回率与准确率",)


def test_realtime_websocket_persists_selected_setup(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("REALTIME_MODE", "mock")
    get_settings.cache_clear()
    profile_root = tmp_path / "interview_profiles" / "候选人甲"
    profile_root.mkdir(parents=True)
    (profile_root / "profile.json").write_text(
        '{"profile_id":"候选人甲","name":"候选人甲","skills":{},"projects":[]}',
        encoding="utf-8",
    )
    with ZipFile(profile_root / "简历.docx", "w") as document:
        document.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>测试简历。</w:t></w:r></w:p></w:body></w:document>',
        )
    jd_root = tmp_path / "interview_job_descriptions"
    jd_root.mkdir()
    (jd_root / "测试岗.md").write_text("# 测试工程师", encoding="utf-8")
    client = TestClient(create_app())

    with client.websocket_connect(
        "/api/interviews/realtime?provider=mock&profile_id=%E5%80%99%E9%80%89%E4%BA%BA%E7%94%B2&resume_name=%E7%AE%80%E5%8E%86.docx&jd_id=%E6%B5%8B%E8%AF%95%E5%B2%97"
    ) as websocket:
        ready = websocket.receive_json()
        websocket.receive_json()
        websocket.send_json({"type": "session.end"})
        websocket.receive_json()

    payload = JsonStorage(tmp_path).read_interview(ready["session_id"])
    assert payload["profile_id"] == "候选人甲"
    assert payload["resume_name"] == "简历.docx"
    assert payload["jd_id"] == "测试岗"
