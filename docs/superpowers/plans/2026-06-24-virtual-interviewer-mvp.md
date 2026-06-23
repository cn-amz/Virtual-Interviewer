# Virtual Interviewer MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first competition MVP for a realtime virtual interviewer with a FastAPI backend, React frontend, mocked realtime mode, profile/JD RAG, tool events, report generation, and ability-tree updates.

**Architecture:** The browser connects only to our FastAPI backend. The backend owns realtime session orchestration, profile/JD loading, tool routing, scoring, report generation, and future Bailian Qwen-Omni-Realtime integration. MVP ships with mock realtime mode so development and tests do not require external API access.

**Tech Stack:** Python 3.11+, FastAPI, pytest, Pydantic, SQLite/JSON file storage for MVP, Node.js 20+, Vite, React, TypeScript, Vitest.

---

## Scope Check

This plan implements the first working slice only:

- Project scaffold
- Backend local session API
- Mock realtime WebSocket
- Profile/JD loading
- Deterministic tool router
- Report and ability tree JSON generation
- Frontend setup/interview/report screens
- Public endpoint abstraction without real tunnel automation

It does not implement production authentication, graph database storage, WebRTC, cloud deployment automation, or final visual polish.

## File Structure

Create or modify these files:

```text
AGENTS.md
.gitignore
README.md
apps/web/package.json
apps/web/index.html
apps/web/vite.config.ts
apps/web/tsconfig.json
apps/web/src/main.tsx
apps/web/src/App.tsx
apps/web/src/api/client.ts
apps/web/src/realtime/useInterviewSession.ts
apps/web/src/pages/SetupPage.tsx
apps/web/src/pages/InterviewPage.tsx
apps/web/src/pages/ReportPage.tsx
apps/web/src/styles.css
services/api/pyproject.toml
services/api/app/__init__.py
services/api/app/main.py
services/api/app/config.py
services/api/app/models.py
services/api/app/storage.py
services/api/app/profile_loader.py
services/api/app/interview_state.py
services/api/app/tool_router.py
services/api/app/scoring.py
services/api/app/ability_tree.py
services/api/app/reporting.py
services/api/app/publish.py
services/api/app/realtime.py
services/api/app/routers/__init__.py
services/api/app/routers/health.py
services/api/app/routers/profiles.py
services/api/app/routers/interviews.py
services/api/tests/test_profile_loader.py
services/api/tests/test_interview_state.py
services/api/tests/test_tool_router.py
services/api/tests/test_ability_tree.py
services/api/tests/test_reporting.py
scripts/dev.ps1
```

## Task 1: Repository Baseline

**Files:**
- Create: `.gitignore`
- Modify: `README.md`

- [ ] **Step 1: Initialize git repository if missing**

Run:

```powershell
git status
```

Expected if not initialized:

```text
fatal: not a git repository
```

Then run:

```powershell
git init
git status --short
```

Expected:

```text
?? AGENTS.md
?? data/
?? docs/
```

- [ ] **Step 2: Create `.gitignore`**

Create `.gitignore` with:

```gitignore
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
node_modules/
dist/
.env
.env.*
!.env.example
.superpowers/
data/interviews/
data/ability_graphs/
*.pyc
*.log
```

- [ ] **Step 3: Create `README.md`**

Create `README.md` with:

```markdown
# Virtual Interviewer

Realtime virtual interviewer for the Southeast University AI+ Innovation Application Competition.

## MVP

- Web frontend for interview setup, realtime mock interview, and report review.
- FastAPI backend for profile/JD loading, tool routing, scoring, reports, and ability tree updates.
- Alibaba Bailian Qwen-Omni-Realtime integration point, with mock mode for local development.

## Local Development

Backend:

```powershell
cd services/api
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd apps/web
npm install
npm run dev
```

Open `http://localhost:5173`.
```

- [ ] **Step 4: Commit repository baseline**

Run:

```powershell
git add .gitignore README.md AGENTS.md docs data/job_descriptions data/profiles/豆瓣酱/config.json data/profiles/豆瓣酱/profile.json data/profiles/豆瓣酱/prompt.txt data/profiles/豆瓣酱/qa_bank.md
git commit -m "docs: capture virtual interviewer design baseline"
```

Expected:

```text
[main ...] docs: capture virtual interviewer design baseline
```

## Task 2: Backend Project Scaffold

**Files:**
- Create: `services/api/pyproject.toml`
- Create: `services/api/app/__init__.py`
- Create: `services/api/app/main.py`
- Create: `services/api/app/config.py`
- Create: `services/api/app/routers/__init__.py`
- Create: `services/api/app/routers/health.py`
- Test: `services/api/tests/test_health.py`

- [ ] **Step 1: Create backend package metadata**

Create `services/api/pyproject.toml`:

```toml
[project]
name = "virtual-interviewer-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "pydantic>=2.8.0",
  "pydantic-settings>=2.4.0",
  "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
  "httpx>=0.27.0",
  "pytest-asyncio>=0.23.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create config module**

Create `services/api/app/config.py`:

```python
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Virtual Interviewer API"
    app_storage_dir: Path = Field(default=Path("../../data"))
    dashscope_api_key: str | None = Field(default=None, alias="DASHSCOPE_API_KEY")
    bailian_realtime_model: str = "qwen3.5-omni-plus-realtime"
    bailian_realtime_url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
    realtime_mode: str = "mock"

    @property
    def data_dir(self) -> Path:
        return self.app_storage_dir.resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: Create health router**

Create `services/api/app/routers/health.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

Create `services/api/app/routers/__init__.py`:

```python
from app.routers import health

__all__ = ["health"]
```

- [ ] **Step 4: Create FastAPI app**

Create `services/api/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    return app


app = create_app()
```

Create `services/api/app/__init__.py`:

```python
__all__ = []
```

- [ ] **Step 5: Write health test**

Create `services/api/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok():
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 6: Run backend tests**

Run:

```powershell
cd services/api
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
.\.venv\Scripts\pytest -q
```

Expected:

```text
1 passed
```

- [ ] **Step 7: Commit backend scaffold**

Run:

```powershell
git add services/api
git commit -m "feat: scaffold FastAPI backend"
```

Expected:

```text
[main ...] feat: scaffold FastAPI backend
```

## Task 3: Profile And JD Loading

**Files:**
- Create: `services/api/app/models.py`
- Create: `services/api/app/profile_loader.py`
- Create: `services/api/app/routers/profiles.py`
- Modify: `services/api/app/main.py`
- Modify: `services/api/app/routers/__init__.py`
- Test: `services/api/tests/test_profile_loader.py`

- [ ] **Step 1: Define shared models**

Create `services/api/app/models.py`:

```python
from pydantic import BaseModel, Field


class ProfileSummary(BaseModel):
    profile_id: str
    name: str
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class JobDescription(BaseModel):
    jd_id: str
    title: str
    content: str


class SessionProfile(BaseModel):
    profile: ProfileSummary
    job_description: JobDescription
    prompt: str
    qa_bank: str
```

- [ ] **Step 2: Implement profile loader**

Create `services/api/app/profile_loader.py`:

```python
import json
from pathlib import Path

from app.models import JobDescription, ProfileSummary, SessionProfile


class ProfileLoader:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def list_profiles(self) -> list[str]:
        profile_dir = self.data_dir / "profiles"
        if not profile_dir.exists():
            return []
        return sorted(path.name for path in profile_dir.iterdir() if path.is_dir())

    def load_profile_summary(self, profile_id: str) -> ProfileSummary:
        profile_path = self.data_dir / "profiles" / profile_id / "profile.json"
        data = json.loads(profile_path.read_text(encoding="utf-8"))
        skills: list[str] = []
        raw_skills = data.get("skills", {})
        if isinstance(raw_skills, dict):
            for values in raw_skills.values():
                if isinstance(values, list):
                    skills.extend(str(item) for item in values)
        projects = [
            str(project.get("name", "")).strip()
            for project in data.get("projects", [])
            if str(project.get("name", "")).strip()
        ]
        return ProfileSummary(
            profile_id=str(data.get("profile_id", profile_id)),
            name=str(data.get("name", profile_id)),
            skills=sorted(set(skills)),
            projects=projects,
        )

    def load_job_description(self, jd_id: str) -> JobDescription:
        jd_path = self.data_dir / "job_descriptions" / f"{jd_id}.md"
        content = jd_path.read_text(encoding="utf-8")
        title = content.splitlines()[0].lstrip("# ").strip()
        return JobDescription(jd_id=jd_id, title=title, content=content)

    def load_session_profile(self, profile_id: str, jd_id: str) -> SessionProfile:
        profile_root = self.data_dir / "profiles" / profile_id
        prompt = (profile_root / "prompt.txt").read_text(encoding="utf-8")
        qa_bank = (profile_root / "qa_bank.md").read_text(encoding="utf-8")
        return SessionProfile(
            profile=self.load_profile_summary(profile_id),
            job_description=self.load_job_description(jd_id),
            prompt=prompt,
            qa_bank=qa_bank,
        )
```

- [ ] **Step 3: Write loader tests**

Create `services/api/tests/test_profile_loader.py`:

```python
from pathlib import Path

from app.profile_loader import ProfileLoader


def test_loader_finds_copied_profile():
    loader = ProfileLoader(Path("../../data").resolve())

    profiles = loader.list_profiles()

    assert "豆瓣酱" in profiles


def test_loader_builds_session_profile():
    loader = ProfileLoader(Path("../../data").resolve())

    session = loader.load_session_profile(
        "豆瓣酱",
        "mechanical-arm-motion-control-algorithm-engineer",
    )

    assert session.profile.name == "豆瓣酱"
    assert "Python" in session.profile.skills
    assert "机械臂" in session.job_description.content
    assert len(session.qa_bank) > 100
```

- [ ] **Step 4: Add profiles router**

Create `services/api/app/routers/profiles.py`:

```python
from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models import SessionProfile
from app.profile_loader import ProfileLoader

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def get_loader(settings: Settings = Depends(get_settings)) -> ProfileLoader:
    return ProfileLoader(settings.data_dir)


@router.get("")
def list_profiles(loader: ProfileLoader = Depends(get_loader)) -> dict[str, list[str]]:
    return {"profiles": loader.list_profiles()}


@router.get("/{profile_id}/session-profile", response_model=SessionProfile)
def get_session_profile(
    profile_id: str,
    jd_id: str = "mechanical-arm-motion-control-algorithm-engineer",
    loader: ProfileLoader = Depends(get_loader),
) -> SessionProfile:
    return loader.load_session_profile(profile_id, jd_id)
```

Modify `services/api/app/routers/__init__.py`:

```python
from app.routers import health, profiles

__all__ = ["health", "profiles"]
```

Modify `services/api/app/main.py` router section:

```python
from app.routers import health, profiles

# inside create_app()
app.include_router(health.router)
app.include_router(profiles.router)
```

- [ ] **Step 5: Run loader tests**

Run:

```powershell
cd services/api
.\.venv\Scripts\pytest tests/test_profile_loader.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Commit profile loader**

Run:

```powershell
git add services/api/app services/api/tests
git commit -m "feat: load candidate profile and target jd"
```

Expected:

```text
[main ...] feat: load candidate profile and target jd
```

## Task 4: Interview State Machine And Tool Router

**Files:**
- Create: `services/api/app/interview_state.py`
- Create: `services/api/app/tool_router.py`
- Test: `services/api/tests/test_interview_state.py`
- Test: `services/api/tests/test_tool_router.py`

- [ ] **Step 1: Implement interview state machine**

Create `services/api/app/interview_state.py`:

```python
from dataclasses import dataclass, field


STAGES = [
    "warmup",
    "resume_overview",
    "project_deep_dive",
    "fundamentals",
    "pressure_followup",
    "candidate_questions",
    "summary",
]


@dataclass
class InterviewState:
    stage: str = "warmup"
    questions_in_stage: int = 0
    low_score_count: int = 0
    history: list[str] = field(default_factory=list)

    def record_answer_score(self, score: float) -> None:
        if score < 3.0:
            self.low_score_count += 1
        self.history.append(f"{self.stage}:{score:.1f}")

    def next_action(self) -> str:
        if self.stage == "warmup":
            return "ask_brief_self_introduction"
        if self.low_score_count >= 2:
            return "ask_targeted_clarification"
        if self.stage == "project_deep_dive":
            return "ask_project_mechanism_followup"
        if self.stage == "summary":
            return "summarize_and_close"
        return "ask_next_stage_question"

    def advance_if_ready(self) -> None:
        self.questions_in_stage += 1
        if self.questions_in_stage < 2:
            return
        current_index = STAGES.index(self.stage)
        if current_index < len(STAGES) - 1:
            self.stage = STAGES[current_index + 1]
            self.questions_in_stage = 0
            self.low_score_count = 0
```

- [ ] **Step 2: Write state tests**

Create `services/api/tests/test_interview_state.py`:

```python
from app.interview_state import InterviewState


def test_state_starts_with_warmup():
    state = InterviewState()

    assert state.stage == "warmup"
    assert state.next_action() == "ask_brief_self_introduction"


def test_state_advances_after_two_questions():
    state = InterviewState()

    state.advance_if_ready()
    assert state.stage == "warmup"
    state.advance_if_ready()

    assert state.stage == "resume_overview"


def test_low_scores_trigger_clarification():
    state = InterviewState(stage="fundamentals")

    state.record_answer_score(2.0)
    state.record_answer_score(2.5)

    assert state.next_action() == "ask_targeted_clarification"
```

- [ ] **Step 3: Implement tool router**

Create `services/api/app/tool_router.py`:

```python
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    name: str
    summary: str
    payload: dict[str, Any]


ToolFunction = Callable[[dict[str, Any]], ToolResult]


class ToolRouter:
    def __init__(self) -> None:
        self._tools: dict[str, ToolFunction] = {}

    def register(self, name: str, func: ToolFunction) -> None:
        if not name.replace("_", "").isalnum():
            raise ValueError(f"invalid tool name: {name}")
        self._tools[name] = func

    def names(self) -> list[str]:
        return sorted(self._tools)

    def call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        if name not in self._tools:
            raise KeyError(f"tool not registered: {name}")
        return self._tools[name](arguments)


def create_default_tool_router() -> ToolRouter:
    router = ToolRouter()

    def retrieve_profile_context(arguments: dict[str, Any]) -> ToolResult:
        query = str(arguments.get("query", ""))
        return ToolResult(
            name="retrieve_profile_context",
            summary=f"Retrieved local profile context for query: {query[:60]}",
            payload={"query": query, "source": "local_profile"},
        )

    def plan_next_question(arguments: dict[str, Any]) -> ToolResult:
        stage = str(arguments.get("stage", "warmup"))
        return ToolResult(
            name="plan_next_question",
            summary=f"Planned next question for stage: {stage}",
            payload={"stage": stage, "question_type": "mechanism_followup"},
        )

    router.register("retrieve_profile_context", retrieve_profile_context)
    router.register("plan_next_question", plan_next_question)
    return router
```

- [ ] **Step 4: Write tool router tests**

Create `services/api/tests/test_tool_router.py`:

```python
import pytest

from app.tool_router import ToolResult, ToolRouter, create_default_tool_router


def test_router_calls_registered_tool():
    router = ToolRouter()
    router.register("echo_tool", lambda args: ToolResult("echo_tool", "ok", args))

    result = router.call("echo_tool", {"value": 1})

    assert result.summary == "ok"
    assert result.payload == {"value": 1}


def test_router_rejects_unknown_tool():
    router = ToolRouter()

    with pytest.raises(KeyError):
        router.call("missing", {})


def test_default_router_has_profile_and_question_tools():
    router = create_default_tool_router()

    assert router.names() == ["plan_next_question", "retrieve_profile_context"]
```

- [ ] **Step 5: Run state and tool tests**

Run:

```powershell
cd services/api
.\.venv\Scripts\pytest tests/test_interview_state.py tests/test_tool_router.py -q
```

Expected:

```text
6 passed
```

- [ ] **Step 6: Commit state and tools**

Run:

```powershell
git add services/api/app/interview_state.py services/api/app/tool_router.py services/api/tests
git commit -m "feat: add interview state and tool router"
```

Expected:

```text
[main ...] feat: add interview state and tool router
```

## Task 5: Scoring, Ability Tree, And Report Generation

**Files:**
- Create: `services/api/app/scoring.py`
- Create: `services/api/app/ability_tree.py`
- Create: `services/api/app/reporting.py`
- Test: `services/api/tests/test_ability_tree.py`
- Test: `services/api/tests/test_reporting.py`

- [ ] **Step 1: Implement scoring**

Create `services/api/app/scoring.py`:

```python
from pydantic import BaseModel


class AnswerScore(BaseModel):
    relevance: float
    technical_depth: float
    evidence_quality: float
    structure: float
    communication: float
    rationale: str

    @property
    def average(self) -> float:
        values = [
            self.relevance,
            self.technical_depth,
            self.evidence_quality,
            self.structure,
            self.communication,
        ]
        return round(sum(values) / len(values), 2)


def score_answer(question: str, answer: str) -> AnswerScore:
    answer_len = len(answer.strip())
    has_numbers = any(ch.isdigit() for ch in answer)
    has_mechanism = any(word in answer for word in ["因为", "通过", "引入", "优化", "实现"])
    depth = 4.0 if has_mechanism else 2.5
    evidence = 4.0 if has_numbers else 3.0
    relevance = 4.0 if answer_len > 20 and question else 2.0
    structure = 4.0 if "。" in answer or "；" in answer else 3.0
    communication = 4.0 if answer_len <= 500 else 3.0
    return AnswerScore(
        relevance=relevance,
        technical_depth=depth,
        evidence_quality=evidence,
        structure=structure,
        communication=communication,
        rationale="Deterministic MVP score based on length, mechanism words, and evidence markers.",
    )
```

- [ ] **Step 2: Implement ability tree**

Create `services/api/app/ability_tree.py`:

```python
from datetime import datetime, timezone
from typing import Any


def empty_ability_tree(user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "skills": [],
        "projects": [],
        "evidence": [],
        "target_skills": [],
        "edges": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def update_tree_from_report(tree: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    updated = {**tree}
    skills = list(updated.get("skills", []))
    evidence = list(updated.get("evidence", []))
    edges = list(updated.get("edges", []))
    for item in report.get("skill_evidence", []):
        skill = item["skill"]
        evidence_id = item["evidence_id"]
        if skill not in skills:
            skills.append(skill)
        if evidence_id not in evidence:
            evidence.append(evidence_id)
        edge = {"from": evidence_id, "to": skill, "type": "supports"}
        if edge not in edges:
            edges.append(edge)
    for gap in report.get("target_gaps", []):
        if gap not in updated.get("target_skills", []):
            updated.setdefault("target_skills", []).append(gap)
    updated["skills"] = skills
    updated["evidence"] = evidence
    updated["edges"] = edges
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()
    return updated
```

- [ ] **Step 3: Implement reporting**

Create `services/api/app/reporting.py`:

```python
from app.scoring import score_answer


def generate_report(user_id: str, interview_id: str, transcript: list[dict[str, str]]) -> dict:
    candidate_answers = [
        item["text"]
        for item in transcript
        if item.get("speaker") == "candidate" and item.get("text")
    ]
    combined_answer = "\n".join(candidate_answers)
    score = score_answer("机械臂运控算法工程师面试", combined_answer)
    skill_evidence = []
    if "ROS" in combined_answer or "ROS2" in combined_answer:
        skill_evidence.append({"skill": "ROS/ROS2", "evidence_id": f"{interview_id}:ros"})
    if "机械臂" in combined_answer or "运动控制" in combined_answer:
        skill_evidence.append({"skill": "机械臂运动控制", "evidence_id": f"{interview_id}:motion_control"})
    if not skill_evidence:
        skill_evidence.append({"skill": "技术表达", "evidence_id": f"{interview_id}:communication"})
    return {
        "user_id": user_id,
        "interview_id": interview_id,
        "summary": "本次面试完成了机械臂运控方向的模拟问答。",
        "score": score.model_dump() | {"average": score.average},
        "skill_evidence": skill_evidence,
        "target_gaps": ["MoveIt规划链路", "控制器参数整定"],
        "next_practice_plan": [
            "用一个项目案例解释机械臂轨迹平滑的输入、处理和输出。",
            "准备 MoveIt 与自研规划链路的差异说明。",
        ],
        "transcript": transcript,
    }
```

- [ ] **Step 4: Write ability tree tests**

Create `services/api/tests/test_ability_tree.py`:

```python
from app.ability_tree import empty_ability_tree, update_tree_from_report


def test_update_tree_adds_supported_skill_and_gap():
    tree = empty_ability_tree("豆瓣酱")
    report = {
        "skill_evidence": [{"skill": "ROS/ROS2", "evidence_id": "int_1:ros"}],
        "target_gaps": ["MoveIt规划链路"],
    }

    updated = update_tree_from_report(tree, report)

    assert "ROS/ROS2" in updated["skills"]
    assert "int_1:ros" in updated["evidence"]
    assert {"from": "int_1:ros", "to": "ROS/ROS2", "type": "supports"} in updated["edges"]
    assert "MoveIt规划链路" in updated["target_skills"]
```

- [ ] **Step 5: Write reporting tests**

Create `services/api/tests/test_reporting.py`:

```python
from app.reporting import generate_report


def test_generate_report_contains_score_and_ability_updates():
    transcript = [
        {"speaker": "assistant", "text": "请介绍机械臂项目"},
        {"speaker": "candidate", "text": "我通过ROS2完成机械臂运动控制，并引入插值算法提升稳定性。"},
    ]

    report = generate_report("豆瓣酱", "int_1", transcript)

    assert report["score"]["average"] >= 3.0
    assert {"skill": "ROS/ROS2", "evidence_id": "int_1:ros"} in report["skill_evidence"]
    assert "MoveIt规划链路" in report["target_gaps"]
```

- [ ] **Step 6: Run report tests**

Run:

```powershell
cd services/api
.\.venv\Scripts\pytest tests/test_ability_tree.py tests/test_reporting.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 7: Commit scoring and reports**

Run:

```powershell
git add services/api/app/scoring.py services/api/app/ability_tree.py services/api/app/reporting.py services/api/tests
git commit -m "feat: generate reports and ability tree updates"
```

Expected:

```text
[main ...] feat: generate reports and ability tree updates
```

## Task 6: Interview Storage And Mock Realtime WebSocket

**Files:**
- Create: `services/api/app/storage.py`
- Create: `services/api/app/realtime.py`
- Create: `services/api/app/routers/interviews.py`
- Modify: `services/api/app/main.py`
- Modify: `services/api/app/routers/__init__.py`
- Test: `services/api/tests/test_interviews.py`

- [ ] **Step 1: Implement JSON storage**

Create `services/api/app/storage.py`:

```python
import json
from pathlib import Path
from typing import Any


class JsonStorage:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        (self.data_dir / "interviews").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "ability_graphs").mkdir(parents=True, exist_ok=True)

    def write_interview(self, interview_id: str, payload: dict[str, Any]) -> Path:
        path = self.data_dir / "interviews" / f"{interview_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def read_interview(self, interview_id: str) -> dict[str, Any]:
        path = self.data_dir / "interviews" / f"{interview_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def write_ability_tree(self, user_id: str, payload: dict[str, Any]) -> Path:
        path = self.data_dir / "ability_graphs" / f"{user_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
```

- [ ] **Step 2: Implement mock realtime session**

Create `services/api/app/realtime.py`:

```python
from uuid import uuid4

from app.interview_state import InterviewState
from app.tool_router import create_default_tool_router


class MockRealtimeSession:
    def __init__(self, profile_id: str, jd_id: str):
        self.session_id = f"iv_{uuid4().hex[:10]}"
        self.profile_id = profile_id
        self.jd_id = jd_id
        self.state = InterviewState()
        self.tool_router = create_default_tool_router()
        self.transcript: list[dict[str, str]] = []

    def start_events(self) -> list[dict]:
        return [
            {"type": "session.ready", "session_id": self.session_id},
            {
                "type": "assistant.text.delta",
                "text": "你好，我是你的虚拟面试官。我们先从一段简短自我介绍开始。",
            },
        ]

    def handle_text(self, text: str) -> list[dict]:
        self.transcript.append({"speaker": "candidate", "text": text})
        tool_result = self.tool_router.call("retrieve_profile_context", {"query": text})
        self.state.record_answer_score(3.5)
        action = self.state.next_action()
        self.state.advance_if_ready()
        reply = "我会结合你的项目继续追问。请具体说明你在机械臂运动控制中改了什么、为什么这样改、效果如何。"
        self.transcript.append({"speaker": "assistant", "text": reply})
        return [
            {"type": "transcript.item", "speaker": "candidate", "text": text},
            {"type": "tool.call", "name": tool_result.name, "arguments": {"query": text}},
            {"type": "tool.result", "name": tool_result.name, "summary": tool_result.summary},
            {"type": "interview.action", "action": action, "stage": self.state.stage},
            {"type": "assistant.text.delta", "text": reply},
        ]
```

- [ ] **Step 3: Implement interview router**

Create `services/api/app/routers/interviews.py`:

```python
from uuid import uuid4

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.ability_tree import empty_ability_tree, update_tree_from_report
from app.config import Settings, get_settings
from app.realtime import MockRealtimeSession
from app.reporting import generate_report
from app.storage import JsonStorage

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


def get_storage(settings: Settings = Depends(get_settings)) -> JsonStorage:
    return JsonStorage(settings.data_dir)


@router.websocket("/realtime")
async def realtime_interview(websocket: WebSocket):
    await websocket.accept()
    session = MockRealtimeSession("豆瓣酱", "mechanical-arm-motion-control-algorithm-engineer")
    for event in session.start_events():
        await websocket.send_json(event)
    try:
        while True:
            event = await websocket.receive_json()
            if event.get("type") == "text.input":
                for output in session.handle_text(str(event.get("text", ""))):
                    await websocket.send_json(output)
            if event.get("type") == "session.end":
                await websocket.send_json({"type": "session.ended", "session_id": session.session_id})
                await websocket.close()
                return
    except WebSocketDisconnect:
        return


@router.post("/mock-report")
def create_mock_report(storage: JsonStorage = Depends(get_storage)) -> dict:
    interview_id = f"int_{uuid4().hex[:10]}"
    transcript = [
        {"speaker": "assistant", "text": "请介绍机械臂项目。"},
        {"speaker": "candidate", "text": "我通过ROS2完成机械臂运动控制，并引入插值算法提升稳定性。"},
    ]
    report = generate_report("豆瓣酱", interview_id, transcript)
    tree = update_tree_from_report(empty_ability_tree("豆瓣酱"), report)
    storage.write_interview(interview_id, {"report": report, "ability_tree": tree})
    storage.write_ability_tree("豆瓣酱", tree)
    return {"interview_id": interview_id, "report": report, "ability_tree": tree}
```

Modify `services/api/app/routers/__init__.py`:

```python
from app.routers import health, interviews, profiles

__all__ = ["health", "interviews", "profiles"]
```

Modify `services/api/app/main.py` router imports and registration:

```python
from app.routers import health, interviews, profiles

app.include_router(health.router)
app.include_router(profiles.router)
app.include_router(interviews.router)
```

- [ ] **Step 4: Write interview report route test**

Create `services/api/tests/test_interviews.py`:

```python
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
```

- [ ] **Step 5: Run interview tests**

Run:

```powershell
cd services/api
.\.venv\Scripts\pytest tests/test_interviews.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit mock realtime and storage**

Run:

```powershell
git add services/api/app services/api/tests
git commit -m "feat: add mock realtime interview flow"
```

Expected:

```text
[main ...] feat: add mock realtime interview flow
```

## Task 7: Publication Provider Interface

**Files:**
- Create: `services/api/app/publish.py`
- Test: `services/api/tests/test_publish.py`

- [ ] **Step 1: Implement publication providers**

Create `services/api/app/publish.py`:

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PublicEndpoint:
    url: str
    provider: str
    notes: list[str]


class PublicEndpointProvider(Protocol):
    def expose(self, local_port: int, protocol: str, purpose: str) -> PublicEndpoint:
        ...


class LocalOnlyProvider:
    def expose(self, local_port: int, protocol: str, purpose: str) -> PublicEndpoint:
        scheme = "http" if protocol in {"http", "ws"} else protocol
        return PublicEndpoint(
            url=f"{scheme}://localhost:{local_port}",
            provider="local",
            notes=[f"Local-only endpoint for {purpose}. Use a tunnel or cloud provider for judges."],
        )


class ReservedProvider:
    def __init__(self, name: str):
        self.name = name

    def expose(self, local_port: int, protocol: str, purpose: str) -> PublicEndpoint:
        return PublicEndpoint(
            url="",
            provider=self.name,
            notes=[
                f"{self.name} provider is reserved for {purpose}.",
                f"Forward local port {local_port} with protocol {protocol} during deployment.",
            ],
        )
```

- [ ] **Step 2: Write publication tests**

Create `services/api/tests/test_publish.py`:

```python
from app.publish import LocalOnlyProvider, ReservedProvider


def test_local_provider_returns_localhost_url():
    endpoint = LocalOnlyProvider().expose(5173, "http", "frontend")

    assert endpoint.url == "http://localhost:5173"
    assert endpoint.provider == "local"


def test_reserved_provider_documents_next_step():
    endpoint = ReservedProvider("frp").expose(8000, "https", "api")

    assert endpoint.url == ""
    assert endpoint.provider == "frp"
    assert "Forward local port 8000" in endpoint.notes[1]
```

- [ ] **Step 3: Run publication tests**

Run:

```powershell
cd services/api
.\.venv\Scripts\pytest tests/test_publish.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 4: Commit publication interface**

Run:

```powershell
git add services/api/app/publish.py services/api/tests/test_publish.py
git commit -m "feat: reserve public endpoint providers"
```

Expected:

```text
[main ...] feat: reserve public endpoint providers
```

## Task 8: Frontend Scaffold

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/index.html`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/src/main.tsx`
- Create: `apps/web/src/App.tsx`
- Create: `apps/web/src/styles.css`

- [ ] **Step 1: Create frontend package**

Create `apps/web/package.json`:

```json
{
  "name": "virtual-interviewer-web",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.4.0",
    "typescript": "^5.5.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "vitest": "^2.0.0"
  }
}
```

- [ ] **Step 2: Create Vite config**

Create `apps/web/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
```

Create `apps/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create app shell**

Create `apps/web/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Virtual Interviewer</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `apps/web/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

Create `apps/web/src/App.tsx`:

```tsx
export function App() {
  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">AI Agent Application Innovation</p>
        <h1>实时通话虚拟面试官</h1>
        <p>
          面向机械臂运控算法工程师岗位，结合百炼实时模型、RAG、工具调用和能力树复盘。
        </p>
      </section>
    </main>
  );
}
```

Create `apps/web/src/styles.css`:

```css
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Inter, "Microsoft YaHei", system-ui, sans-serif;
  background: #f8fafc;
  color: #0f172a;
}

.app-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
}

.hero {
  width: min(920px, 100%);
  padding: 32px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #ffffff;
}

.eyebrow {
  margin: 0 0 12px;
  color: #2563eb;
  font-weight: 700;
}

h1 {
  margin: 0 0 16px;
  font-size: 40px;
  line-height: 1.1;
}

p {
  line-height: 1.7;
}
```

- [ ] **Step 4: Build frontend**

Run:

```powershell
cd apps/web
npm install
npm run build
```

Expected:

```text
✓ built
```

- [ ] **Step 5: Commit frontend scaffold**

Run:

```powershell
git add apps/web
git commit -m "feat: scaffold web frontend"
```

Expected:

```text
[main ...] feat: scaffold web frontend
```

## Task 9: Frontend Interview Flow

**Files:**
- Create: `apps/web/src/api/client.ts`
- Create: `apps/web/src/realtime/useInterviewSession.ts`
- Create: `apps/web/src/pages/SetupPage.tsx`
- Create: `apps/web/src/pages/InterviewPage.tsx`
- Create: `apps/web/src/pages/ReportPage.tsx`
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/styles.css`

- [ ] **Step 1: Create API client**

Create `apps/web/src/api/client.ts`:

```ts
export const API_BASE = "http://localhost:8000";

export type ProfileList = {
  profiles: string[];
};

export async function listProfiles(): Promise<ProfileList> {
  const response = await fetch(`${API_BASE}/api/profiles`);
  if (!response.ok) {
    throw new Error(`Failed to load profiles: ${response.status}`);
  }
  return response.json();
}

export async function createMockReport() {
  const response = await fetch(`${API_BASE}/api/interviews/mock-report`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Failed to create report: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 2: Create realtime hook**

Create `apps/web/src/realtime/useInterviewSession.ts`:

```ts
import { useRef, useState } from "react";

export type RealtimeEvent = {
  type: string;
  text?: string;
  speaker?: string;
  name?: string;
  summary?: string;
  stage?: string;
  action?: string;
};

export function useInterviewSession() {
  const socketRef = useRef<WebSocket | null>(null);
  const [events, setEvents] = useState<RealtimeEvent[]>([]);
  const [connected, setConnected] = useState(false);

  function start() {
    const socket = new WebSocket("ws://localhost:8000/api/interviews/realtime");
    socketRef.current = socket;
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (message) => {
      setEvents((prev) => [...prev, JSON.parse(message.data)]);
    };
  }

  function sendText(text: string) {
    socketRef.current?.send(JSON.stringify({ type: "text.input", text }));
  }

  function end() {
    socketRef.current?.send(JSON.stringify({ type: "session.end" }));
  }

  return { connected, events, start, sendText, end };
}
```

- [ ] **Step 3: Create setup page**

Create `apps/web/src/pages/SetupPage.tsx`:

```tsx
type SetupPageProps = {
  onStart: () => void;
};

export function SetupPage({ onStart }: SetupPageProps) {
  return (
    <section className="panel">
      <p className="eyebrow">MVP Setup</p>
      <h1>机械臂运控算法工程师模拟面试</h1>
      <p>候选人：豆瓣酱。目标岗位：机械臂运控算法工程师。</p>
      <button className="primary-button" onClick={onStart}>
        开始模拟面试
      </button>
    </section>
  );
}
```

- [ ] **Step 4: Create interview page**

Create `apps/web/src/pages/InterviewPage.tsx`:

```tsx
import { useState } from "react";
import { useInterviewSession } from "../realtime/useInterviewSession";

type InterviewPageProps = {
  onFinish: () => void;
};

export function InterviewPage({ onFinish }: InterviewPageProps) {
  const { connected, events, start, sendText, end } = useInterviewSession();
  const [answer, setAnswer] = useState("我通过ROS2完成机械臂运动控制，并引入插值算法提升稳定性。");

  return (
    <section className="interview-grid">
      <div className="panel">
        <p className="eyebrow">Realtime Interview</p>
        <h1>虚拟面试官</h1>
        <p>连接状态：{connected ? "已连接" : "未连接"}</p>
        <div className="button-row">
          <button className="primary-button" onClick={start}>连接面试官</button>
          <button className="secondary-button" onClick={() => sendText(answer)}>发送模拟回答</button>
          <button className="secondary-button" onClick={() => { end(); onFinish(); }}>结束并生成报告</button>
        </div>
        <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} />
      </div>
      <div className="panel">
        <h2>事件流</h2>
        <div className="event-list">
          {events.map((event, index) => (
            <div className="event-item" key={`${event.type}-${index}`}>
              <strong>{event.type}</strong>
              <span>{event.text || event.summary || event.action || event.stage}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Create report page**

Create `apps/web/src/pages/ReportPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { createMockReport } from "../api/client";

export function ReportPage() {
  const [report, setReport] = useState<any>(null);

  useEffect(() => {
    createMockReport().then(setReport).catch((error) => {
      setReport({ error: String(error) });
    });
  }, []);

  if (!report) {
    return <section className="panel">报告生成中...</section>;
  }

  if (report.error) {
    return <section className="panel">报告生成失败：{report.error}</section>;
  }

  return (
    <section className="panel">
      <p className="eyebrow">Post Interview Report</p>
      <h1>能力树复盘</h1>
      <p>{report.report.summary}</p>
      <h2>平均分：{report.report.score.average}</h2>
      <h2>成长树枝</h2>
      <ul>
        {report.ability_tree.skills.map((skill: string) => (
          <li key={skill}>{skill}</li>
        ))}
      </ul>
      <h2>虚拟树枝</h2>
      <ul>
        {report.ability_tree.target_skills.map((skill: string) => (
          <li key={skill}>{skill}</li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 6: Wire pages in App**

Modify `apps/web/src/App.tsx`:

```tsx
import { useState } from "react";
import { InterviewPage } from "./pages/InterviewPage";
import { ReportPage } from "./pages/ReportPage";
import { SetupPage } from "./pages/SetupPage";

type Screen = "setup" | "interview" | "report";

export function App() {
  const [screen, setScreen] = useState<Screen>("setup");

  return (
    <main className="app-shell">
      {screen === "setup" && <SetupPage onStart={() => setScreen("interview")} />}
      {screen === "interview" && <InterviewPage onFinish={() => setScreen("report")} />}
      {screen === "report" && <ReportPage />}
    </main>
  );
}
```

- [ ] **Step 7: Extend CSS**

Append to `apps/web/src/styles.css`:

```css
.panel {
  width: min(980px, 100%);
  padding: 28px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #ffffff;
}

.interview-grid {
  width: min(1180px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 420px);
  gap: 20px;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 18px 0;
}

.primary-button,
.secondary-button {
  border: 0;
  border-radius: 8px;
  padding: 11px 16px;
  font-weight: 700;
  cursor: pointer;
}

.primary-button {
  background: #2563eb;
  color: #ffffff;
}

.secondary-button {
  background: #e0ecff;
  color: #1e3a8a;
}

textarea {
  width: 100%;
  min-height: 120px;
  padding: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  resize: vertical;
}

.event-list {
  display: grid;
  gap: 10px;
}

.event-item {
  display: grid;
  gap: 4px;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

@media (max-width: 860px) {
  .interview-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 8: Build frontend**

Run:

```powershell
cd apps/web
npm run build
```

Expected:

```text
✓ built
```

- [ ] **Step 9: Commit frontend flow**

Run:

```powershell
git add apps/web/src
git commit -m "feat: add interview and report frontend flow"
```

Expected:

```text
[main ...] feat: add interview and report frontend flow
```

## Task 10: Developer Script And Full Verification

**Files:**
- Create: `scripts/dev.ps1`
- Modify: `README.md`

- [ ] **Step 1: Create development helper**

Create `scripts/dev.ps1`:

```powershell
param(
    [ValidateSet("backend", "frontend")]
    [string]$Target = "backend"
)

$Root = Split-Path -Parent $PSScriptRoot

if ($Target -eq "backend") {
    Set-Location "$Root\services\api"
    if (-not (Test-Path ".venv")) {
        python -m venv .venv
    }
    .\.venv\Scripts\pip install -e ".[dev]"
    .\.venv\Scripts\uvicorn app.main:app --reload --port 8000
}

if ($Target -eq "frontend") {
    Set-Location "$Root\apps\web"
    if (-not (Test-Path "node_modules")) {
        npm install
    }
    npm run dev
}
```

- [ ] **Step 2: Update README commands**

Add to `README.md`:

```markdown
## Dev Scripts

Start backend:

```powershell
.\scripts\dev.ps1 backend
```

Start frontend in a second terminal:

```powershell
.\scripts\dev.ps1 frontend
```
```

- [ ] **Step 3: Run full backend tests**

Run:

```powershell
cd services/api
.\.venv\Scripts\pytest -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 4: Run frontend build**

Run:

```powershell
cd apps/web
npm run build
```

Expected:

```text
✓ built
```

- [ ] **Step 5: Manual smoke test**

Run backend:

```powershell
.\scripts\dev.ps1 backend
```

Run frontend in another terminal:

```powershell
.\scripts\dev.ps1 frontend
```

Open:

```text
http://localhost:5173
```

Expected:

- Setup page loads.
- Clicking start opens interview page.
- Clicking connect shows connected state.
- Sending simulated answer adds transcript, tool, action, and assistant events.
- Ending interview opens report page.
- Report page shows average score, growth branches, and virtual branches.

- [ ] **Step 6: Commit developer workflow**

Run:

```powershell
git add scripts README.md
git commit -m "chore: add local development workflow"
```

Expected:

```text
[main ...] chore: add local development workflow
```

## Task 11: Prepare For Bailian Live Adapter

**Files:**
- Create: `services/api/app/integrations/__init__.py`
- Create: `services/api/app/integrations/bailian/__init__.py`
- Create: `services/api/app/integrations/bailian/omni_realtime.py`
- Test: `services/api/tests/test_bailian_adapter.py`

- [ ] **Step 1: Create integration package**

Create `services/api/app/integrations/__init__.py`:

```python
__all__ = []
```

Create `services/api/app/integrations/bailian/__init__.py`:

```python
__all__ = []
```

- [ ] **Step 2: Create live adapter guard**

Create `services/api/app/integrations/bailian/omni_realtime.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class BailianRealtimeConfig:
    api_key: str | None
    model: str
    url: str


class BailianRealtimeAdapter:
    def __init__(self, config: BailianRealtimeConfig):
        self.config = config

    def validate_ready(self) -> None:
        if not self.config.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is required for Bailian live realtime mode.")
        if not self.config.model:
            raise RuntimeError("Bailian realtime model is required.")
        if not self.config.url.startswith("wss://"):
            raise RuntimeError("Bailian realtime URL must start with wss://.")
```

- [ ] **Step 3: Write adapter tests**

Create `services/api/tests/test_bailian_adapter.py`:

```python
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
```

- [ ] **Step 4: Run adapter tests**

Run:

```powershell
cd services/api
.\.venv\Scripts\pytest tests/test_bailian_adapter.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit live adapter guard**

Run:

```powershell
git add services/api/app/integrations services/api/tests/test_bailian_adapter.py
git commit -m "feat: prepare Bailian realtime adapter"
```

Expected:

```text
[main ...] feat: prepare Bailian realtime adapter
```

## Plan Self-Review

### Spec Coverage

- Competition deliverables: Task 1 docs, Task 10 dev workflow, publication interface in Task 7.
- Web App + FastAPI: Tasks 2, 8, 9.
- Profile and JD: Task 3.
- Realtime mock session: Task 6.
- Tool Calling visibility: Tasks 4, 6, 9.
- Report and ability tree: Tasks 5, 6, 9.
- Bailian live extension point: Task 11.
- Public endpoint abstraction: Task 7.

### Placeholder Scan

The plan contains no unresolved placeholder markers. Reserved providers are intentionally implemented as explicit extension points with testable behavior.

### Type Consistency

The event fields, report fields, and ability tree fields match across backend services and frontend consumers. The profile and JD IDs match the files already present under `data/`.

