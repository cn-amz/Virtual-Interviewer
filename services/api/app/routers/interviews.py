import asyncio
from contextlib import suppress
from uuid import uuid4

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.ability_tree import empty_ability_tree, update_tree_from_report
from app.auth import get_optional_current_user
from app.config import Settings, get_settings
from app.integrations.bailian.omni_realtime import BailianRealtimeAdapter, BailianRealtimeConfig
from app.profile_loader import ProfileLoader
from app.realtime import MockRealtimeSession
from app.realtime_gateway import RealtimeGateway
from app.reporting import generate_report
from app.storage import JsonStorage

router = APIRouter(prefix="/api/interviews", tags=["interviews"])

DEFAULT_PROFILE_ID = "豆瓣酱"
DEFAULT_JD_ID = "mechanical-arm-motion-control-algorithm-engineer"


def get_storage(settings: Settings = Depends(get_settings)) -> JsonStorage:
    return JsonStorage(settings.data_dir)


def create_realtime_session(settings: Settings):
    if settings.realtime_mode == "bailian":
        context = load_interview_context(settings)
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
            )
        )
    return MockRealtimeSession(DEFAULT_PROFILE_ID, DEFAULT_JD_ID)


def load_interview_context(settings: Settings) -> dict:
    try:
        loader = ProfileLoader(settings.data_dir)
        profile = loader.load_profile_summary(DEFAULT_PROFILE_ID)
        jd = loader.load_job_description(DEFAULT_JD_ID)
        return {
            "candidate_name": profile.name,
            "target_role": normalize_role_title(jd.title),
            "resume_projects": tuple(profile.projects),
            "resume_skills": tuple(profile.skills),
        }
    except Exception:
        return {
            "candidate_name": DEFAULT_PROFILE_ID,
            "target_role": "机械臂运控算法工程师",
            "resume_projects": ("ROS2 机械臂运动控制",),
            "resume_skills": ("ROS2", "机械臂运动控制", "轨迹规划", "插值算法"),
        }


def normalize_role_title(title: str) -> str:
    return title.replace("目标岗位：", "").replace("目标岗位:", "").strip()


@router.websocket("/realtime")
async def realtime_interview(websocket: WebSocket, settings: Settings = Depends(get_settings)):
    await websocket.accept()

    session = create_realtime_session(settings)
    realtime_connected = False
    if settings.realtime_mode == "bailian":
        try:
            await session.connect()
            realtime_connected = True
        except (RuntimeError, NotImplementedError) as exc:
            await websocket.send_json({"type": "realtime.error", "message": str(exc)})
            if settings.text_mode != "bailian_text":
                await websocket.close()
                return

    gateway = RealtimeGateway(session)
    for event in await gateway.start_events():
        await websocket.send_json(event)

    relay_task = None
    if realtime_connected and hasattr(session, "receive_events"):
        relay_task = asyncio.create_task(relay_realtime_events(websocket, session))

    try:
        while True:
            event = await websocket.receive_json()
            for output in await gateway.dispatch(event):
                await websocket.send_json(output)
            if event.get("type") == "session.end":
                await websocket.close()
                return
    except WebSocketDisconnect:
        return
    finally:
        if relay_task:
            relay_task.cancel()
            with suppress(asyncio.CancelledError):
                await relay_task
        if hasattr(session, "close"):
            await session.close()


async def relay_realtime_events(websocket: WebSocket, session) -> None:
    while True:
        for event in await session.receive_events():
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
    return {"interview_id": interview_id, "report": report, "ability_tree": tree}
