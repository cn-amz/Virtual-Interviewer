import asyncio
from contextlib import suppress
from uuid import uuid4

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.ability_tree import empty_ability_tree, update_tree_from_report
from app.config import Settings, get_settings
from app.integrations.bailian.omni_realtime import BailianRealtimeAdapter, BailianRealtimeConfig
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
        return BailianRealtimeAdapter(
            BailianRealtimeConfig(
                api_key=settings.dashscope_api_key,
                model=settings.bailian_realtime_model,
                url=settings.bailian_realtime_url,
            )
        )
    return MockRealtimeSession(DEFAULT_PROFILE_ID, DEFAULT_JD_ID)


@router.websocket("/realtime")
async def realtime_interview(
    websocket: WebSocket, settings: Settings = Depends(get_settings)
):
    await websocket.accept()

    session = create_realtime_session(settings)
    if settings.realtime_mode == "bailian":
        try:
            await session.connect()
        except (RuntimeError, NotImplementedError) as exc:
            await websocket.send_json({"type": "realtime.error", "message": str(exc)})
            await websocket.close()
            return

    gateway = RealtimeGateway(session)
    for event in await gateway.start_events():
        await websocket.send_json(event)

    relay_task = None
    if hasattr(session, "receive_events"):
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
def create_mock_report(storage: JsonStorage = Depends(get_storage)) -> dict:
    interview_id = f"int_{uuid4().hex[:10]}"
    transcript = [
        {"speaker": "assistant", "text": "请介绍机械臂项目。"},
        {
            "speaker": "candidate",
            "text": "我通过ROS2完成机械臂运动控制，并引入插值算法提升稳定性。",
        },
    ]
    report = generate_report(DEFAULT_PROFILE_ID, interview_id, transcript)
    tree = update_tree_from_report(empty_ability_tree(DEFAULT_PROFILE_ID), report)
    storage.write_interview(interview_id, {"report": report, "ability_tree": tree})
    storage.write_ability_tree(DEFAULT_PROFILE_ID, tree)
    return {"interview_id": interview_id, "report": report, "ability_tree": tree}
