import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from websockets.exceptions import WebSocketException

from app.ability_tree import empty_ability_tree, update_tree_from_report
from app.auth import get_current_user, get_optional_current_user
from app.config import Settings, get_settings
from app.integrations.bailian.omni_realtime import BailianRealtimeAdapter, BailianRealtimeConfig
from app.integrations.bailian.text_client import BailianTextClient, BailianTextConfig
from app.integrations.minicpm.realtime import MiniCPMRealtimeAdapter, MiniCPMRealtimeConfig
from app.interview_ledger import InterviewLedger
from app.profile_loader import ProfileLoader
from app.realtime import MockRealtimeSession
from app.realtime_gateway import RealtimeGateway
from app.reporting import generate_analyzed_report, generate_report
from app.storage import JsonStorage
from app.ability_tree_markdown import write_ability_tree_markdown

router = APIRouter(prefix="/api/interviews", tags=["interviews"])

DEFAULT_PROFILE_ID = "豆瓣酱"
DEFAULT_JD_ID = "mechanical-arm-motion-control-algorithm-engineer"
MAX_JOB_DESCRIPTION_CONTEXT_CHARS = 8_000


def get_storage(settings: Settings = Depends(get_settings)) -> JsonStorage:
    return JsonStorage(settings.data_dir)


def create_realtime_session(
    settings: Settings,
    *,
    provider: str | None = None,
    context: dict | None = None,
):
    realtime_mode = provider or settings.realtime_mode
    context = context or load_interview_context(settings)
    if realtime_mode == "bailian":
        return BailianRealtimeAdapter(
            BailianRealtimeConfig(
                api_key=settings.dashscope_api_key,
                model=settings.bailian_realtime_model,
                url=settings.bailian_realtime_url,
                text_mode=settings.text_mode,
                text_model=settings.bailian_text_model,
                text_base_url=settings.bailian_text_base_url,
                candidate_name=context["candidate_name"],
                target_role=context["target_role"],
                resume_projects=context["resume_projects"],
                resume_skills=context["resume_skills"],
                role_direction=context["role_direction"],
                interview_focus=context["interview_focus"],
                question_strategy=context["question_strategy"],
                initial_prompt=context["initial_prompt"],
                resume_text=context["resume_text"],
                job_description_text=context["job_description_text"],
            )
        )
    if realtime_mode == "minicpm":
        return MiniCPMRealtimeAdapter(
            MiniCPMRealtimeConfig(
                url=settings.minicpm_realtime_url,
                candidate_name=context["candidate_name"],
                target_role=context["target_role"],
                resume_projects=context["resume_projects"],
                resume_skills=context["resume_skills"],
                role_direction=context["role_direction"],
                interview_focus=context["interview_focus"],
                initial_prompt=context["initial_prompt"],
                resume_text=context["resume_text"],
            )
        )
    if realtime_mode == "mock":
        return MockRealtimeSession(context["profile_id"], context["jd_id"])
    raise ValueError(f"Unsupported realtime provider: {realtime_mode}")


def load_interview_context(
    settings: Settings,
    *,
    profile_id: str = DEFAULT_PROFILE_ID,
    resume_name: str = "",
    jd_id: str = DEFAULT_JD_ID,
) -> dict:
    try:
        loader = ProfileLoader(settings.data_dir)
        profile = loader.load_profile_summary(profile_id)
        jd = loader.load_job_description(jd_id)
        analysis = loader.get_job_description_analysis(jd_id)
        return {
            "profile_id": profile_id,
            "jd_id": jd_id,
            "resume_name": resume_name,
            "candidate_name": profile.name,
            "target_role": normalize_role_title(jd.title),
            "resume_projects": tuple(profile.projects),
            "resume_skills": tuple(profile.skills),
            "role_direction": analysis.role_direction if analysis else "机器人运动规划与控制工程",
            "interview_focus": tuple(analysis.focus_points) if analysis else (),
            "question_strategy": tuple(analysis.question_strategy) if analysis else (),
            "initial_prompt": analysis.initial_prompt if analysis else "",
            "resume_text": loader.load_resume_text(profile_id, resume_name) if resume_name else "",
            "job_description_text": jd.content[:MAX_JOB_DESCRIPTION_CONTEXT_CHARS],
        }
    except Exception:
        if profile_id != DEFAULT_PROFILE_ID or jd_id != DEFAULT_JD_ID or resume_name:
            raise
        return {
            "profile_id": DEFAULT_PROFILE_ID,
            "jd_id": DEFAULT_JD_ID,
            "resume_name": "",
            "candidate_name": DEFAULT_PROFILE_ID,
            "target_role": "机械臂运控算法工程师",
            "resume_projects": ("ROS2 机械臂运动控制",),
            "resume_skills": ("ROS2", "机械臂运动控制", "轨迹规划", "插值算法"),
            "role_direction": "机械臂规划、控制与操作",
            "interview_focus": ("运动学/逆运动学与 MoveIt", "轨迹规划、平滑和碰撞检测", "仿真到真机验证"),
            "question_strategy": ("先核验项目职责，再追问指标与工程取舍",),
            "initial_prompt": "优先核验候选人的机械臂规划、控制和真机部署证据。",
            "resume_text": "",
            "job_description_text": "机械臂运动控制、轨迹规划、MoveIt 与真机部署。",
        }


def normalize_role_title(title: str) -> str:
    return title.replace("目标岗位：", "").replace("目标岗位:", "").strip()


def normalize_minicpm_status(status: object) -> dict:
    offline = {
        "provider": "minicpm",
        "state": "offline",
        "detail": "MiniCPM 服务不可用",
        "queue_length": 0,
    }
    if not isinstance(status, dict):
        return offline
    counts = {}
    for field in (
        "idle_workers",
        "loading_workers",
        "busy_workers",
        "duplex_workers",
        "error_workers",
        "queue_length",
    ):
        value = status.get(field, 0)
        if type(value) is not int or value < 0:
            return offline
        counts[field] = value

    queue_length = counts["queue_length"]
    if status.get("error") or counts["error_workers"]:
        state, detail = "error", "MiniCPM 服务异常"
    elif counts["loading_workers"]:
        state, detail = "loading", "模型正在加载或重置"
    elif counts["busy_workers"] or counts["duplex_workers"]:
        state, detail = "busy", "模型正在处理中"
    elif queue_length:
        state, detail = "queued", "请求排队中"
    elif counts["idle_workers"]:
        state, detail = "idle", "模型已就绪"
    else:
        return offline
    return {
        "provider": "minicpm",
        "state": state,
        "detail": detail,
        "queue_length": queue_length,
    }


async def fetch_minicpm_status(url: str) -> object:
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(url, timeout=5)
    response.raise_for_status()
    return response.json()


async def resolve_provider_status(
    provider: str,
    settings: Settings,
    loader: Callable[[str], Awaitable[object]] | None = None,
) -> dict:
    if provider == "bailian":
        if settings.dashscope_api_key:
            return {"provider": "bailian", "state": "idle", "detail": "百炼服务已配置", "queue_length": 0}
        return {"provider": "bailian", "state": "offline", "detail": "百炼服务未配置", "queue_length": 0}
    if provider == "minicpm":
        loader = loader or fetch_minicpm_status
        try:
            return normalize_minicpm_status(await loader(settings.minicpm_status_url))
        except Exception:
            return normalize_minicpm_status(None)
    raise ValueError(f"Unsupported provider: {provider}")


@router.get("/providers/{provider}/status")
async def get_provider_status(
    provider: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        return await resolve_provider_status(provider, settings)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.websocket("/realtime")
async def realtime_interview(websocket: WebSocket, settings: Settings = Depends(get_settings)):
    await websocket.accept()

    provider = websocket.query_params.get("provider") or settings.realtime_mode
    profile_id = websocket.query_params.get("profile_id") or DEFAULT_PROFILE_ID
    resume_name = websocket.query_params.get("resume_name") or ""
    jd_id = websocket.query_params.get("jd_id") or DEFAULT_JD_ID
    try:
        context = load_interview_context(
            settings,
            profile_id=profile_id,
            resume_name=resume_name,
            jd_id=jd_id,
        )
        session = create_realtime_session(settings, provider=provider, context=context)
    except (FileNotFoundError, ValueError) as exc:
        await websocket.send_json({"type": "realtime.error", "message": str(exc)})
        await websocket.close(code=1008)
        return

    interview_id = getattr(session, "session_id", f"iv_{uuid4().hex[:10]}")
    ledger = InterviewLedger(
        interview_id,
        context["profile_id"],
        context["profile_id"],
        context["jd_id"],
        context["resume_name"],
        authoritative_asr=(
            "provider_asr" if provider == "bailian" else "browser_asr" if provider == "minicpm" else "application"
        ),
    )
    realtime_connected = False
    status = "disconnected"
    close_reason = "browser_disconnect"
    persisted = False
    storage = JsonStorage(settings.data_dir)
    if provider in {"bailian", "minicpm"}:
        try:
            await asyncio.wait_for(session.connect(), timeout=45)
            realtime_connected = True
        except (asyncio.TimeoutError, RuntimeError, NotImplementedError, WebSocketException) as exc:
            if hasattr(session, "close"):
                await session.close()
            message = (
                "等待本地 MiniCPM Worker 就绪超时；请结束其他本地会话后重试。"
                if isinstance(exc, asyncio.TimeoutError) and provider == "minicpm"
                else str(exc)
            )
            await websocket.send_json({"type": "realtime.error", "message": message})
            if settings.text_mode != "bailian_text":
                await websocket.close()
                return

    gateway = RealtimeGateway(session)
    for event in await gateway.start_events():
        ledger.record("server", event)
        await websocket.send_json(event)

    relay_task = None
    if realtime_connected and hasattr(session, "receive_events"):
        relay_task = asyncio.create_task(relay_realtime_events(websocket, session, ledger))

    async def stop_realtime() -> None:
        nonlocal relay_task
        if relay_task:
            relay_task.cancel()
            with suppress(asyncio.CancelledError):
                await relay_task
            relay_task = None
        if hasattr(session, "close"):
            await session.close()

    def persist(final_status: str, reason: str) -> None:
        nonlocal persisted
        if persisted:
            return
        storage.write_interview(
            interview_id,
            ledger.payload(status=final_status, close_reason=reason),
        )
        persisted = True

    try:
        while True:
            event = await websocket.receive_json()
            event_type = event.get("type")
            if event_type == "session.end":
                status = "completed"
                close_reason = "client_session_end"
            elif event_type == "session.cancel":
                status = "cancelled"
                close_reason = "client_session_cancel"
            ledger.record("client", event)
            for output in await gateway.dispatch(event):
                ledger.record("server", output)
                await websocket.send_json(output)
            if event_type in {"session.end", "session.cancel"}:
                await stop_realtime()
                persist(status, close_reason)
                await websocket.send_json(
                    {"type": "session.persisted", "session_id": interview_id, "status": status}
                )
                await websocket.close()
                return
    except WebSocketDisconnect:
        return
    finally:
        await stop_realtime()
        persist(status, close_reason)


async def relay_realtime_events(websocket: WebSocket, session, ledger: InterviewLedger) -> None:
    try:
        while True:
            for event in await session.receive_events():
                ledger.record("provider", event)
                await websocket.send_json(event)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        event = {"type": "realtime.error", "message": f"上游实时连接异常：{exc}"}
        ledger.record("server", event)
        with suppress(Exception):
            await websocket.send_json(event)


@router.post("/mock-report")
def create_mock_report(
    storage: JsonStorage = Depends(get_storage),
    current_user: dict | None = Depends(get_optional_current_user),
) -> dict:
    user_id = current_user["user_id"] if current_user else DEFAULT_PROFILE_ID
    interview_id = f"int_{uuid4().hex[:10]}"
    transcript = [
        {"speaker": "assistant", "text": "请介绍机械臂项目。"},
        {
            "speaker": "candidate",
            "text": "我通过 ROS2 完成机械臂运动控制，并引入插值算法提升稳定性。",
        },
    ]
    report = generate_report(user_id, interview_id, transcript)
    tree = update_tree_from_report(empty_ability_tree(user_id), report)
    storage.write_interview(interview_id, {"report": report, "ability_tree": tree})
    storage.write_ability_tree(user_id, tree)
    write_ability_tree_markdown(storage.data_dir, user_id, tree)
    return {"interview_id": interview_id, "report": report, "ability_tree": tree}


@router.get("/history")
def list_interview_history(
    storage: JsonStorage = Depends(get_storage),
    _current_user: dict = Depends(get_current_user),
) -> list[dict]:
    return storage.list_interviews()


@router.get("/{interview_id}")
def get_interview_history(
    interview_id: str,
    storage: JsonStorage = Depends(get_storage),
    _current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        return storage.read_interview(interview_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Interview report not found") from exc


@router.post("/{interview_id}/analyze")
async def analyze_interview(
    interview_id: str,
    settings: Settings = Depends(get_settings),
    storage: JsonStorage = Depends(get_storage),
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        payload = storage.read_interview(interview_id)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Interview session not found") from exc
    if payload.get("report"):
        return {
            "interview_id": interview_id,
            "report": payload["report"],
            "ability_tree": payload.get("ability_tree", {}),
        }

    transcript = payload.get("transcript", [])
    if not transcript:
        raise HTTPException(status_code=422, detail="Interview transcript is empty")
    text_client = None
    if settings.text_mode == "bailian_text":
        text_client = BailianTextClient(
            BailianTextConfig(
                api_key=settings.dashscope_api_key,
                model=settings.bailian_text_model,
                base_url=settings.bailian_text_base_url,
            ),
            system_prompt="你是面试复盘分析器，只输出符合要求的 JSON。",
        )
    user_id = current_user["user_id"]
    report = await generate_analyzed_report(
        user_id,
        interview_id,
        transcript,
        text_client=text_client,
    )
    tree = storage.read_ability_tree(user_id) or empty_ability_tree(user_id)
    tree = update_tree_from_report(tree, report)
    payload["report"] = report
    payload["ability_tree"] = tree
    payload["user_id"] = user_id
    storage.write_interview(interview_id, payload)
    storage.write_ability_tree(user_id, tree)
    write_ability_tree_markdown(storage.data_dir, user_id, tree)
    return {"interview_id": interview_id, "report": report, "ability_tree": tree}
