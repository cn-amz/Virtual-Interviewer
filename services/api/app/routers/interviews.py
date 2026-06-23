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
