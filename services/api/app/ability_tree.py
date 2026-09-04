from datetime import datetime, timezone
from typing import Any


KNOWLEDGE_POINT_LIBRARY: dict[str, list[dict[str, str]]] = {
    "ROS/ROS2": [
        {"title": "ROS2 通信、DDS 与 QoS", "summary": "关注节点通信、可靠性、延迟和历史缓存策略。", "obsidian_ref": "[[机械臂运控知识点]]"},
        {"title": "ROS2 节点与生命周期", "summary": "关注节点配置、激活、停止和故障恢复。", "obsidian_ref": "[[机械臂运控知识点]]"},
    ],
    "机械臂运动控制": [
        {"title": "轨迹插值与时间参数化", "summary": "把离散规划点变成位置、速度、加速度连续的可执行轨迹。", "obsidian_ref": "[[机械臂运控知识点]]"},
        {"title": "控制周期与速度加速度约束", "summary": "关注模型输出频率、控制器周期、限幅和时间戳对齐。", "obsidian_ref": "[[机械臂运控知识点]]"},
        {"title": "闭环控制与阻抗控制", "summary": "结合误差反馈、负载和接触场景判断控制模式与参数。", "obsidian_ref": "[[机械臂运控知识点]]"},
    ],
    "技术表达": [
        {"title": "项目问题的 STAR 表达", "summary": "说明背景、个人动作、技术原因、量化结果和反思。", "obsidian_ref": "[[面试评分体系]]"},
    ],
}


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
    evidence_details = list(updated.get("evidence_details", []))
    answer_turns = _answer_turns(report.get("transcript", []))
    for item in report.get("skill_evidence", []):
        skill = str(item["skill"])
        evidence_id = str(item["evidence_id"])
        if skill not in skills:
            skills.append(skill)
        if evidence_id not in evidence:
            evidence.append(evidence_id)
        edge = {"from": evidence_id, "to": skill, "type": "supports"}
        if edge not in edges:
            edges.append(edge)
        detail = _build_evidence_detail(report, item, answer_turns)
        evidence_details = [entry for entry in evidence_details if entry.get("evidence_id") != evidence_id]
        evidence_details.append(detail)
    for gap in report.get("target_gaps", []):
        if gap not in updated.get("target_skills", []):
            updated.setdefault("target_skills", []).append(gap)
    updated["skills"] = skills
    updated["evidence"] = evidence
    updated["edges"] = edges
    updated["evidence_details"] = evidence_details
    for key in ("question_groups", "type_branches", "organization_mode", "organization_error"):
        updated.pop(key, None)
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()
    return updated


def hydrate_tree_from_reports(tree: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    """Backfill evidence details for trees created before the detail schema existed."""
    hydrated = tree
    known_ids = {str(item.get("evidence_id")) for item in tree.get("evidence_details", [])}
    for record in records:
        report = record.get("report") or {}
        owner_id = report.get("user_id") or record.get("user_id")
        if owner_id == tree.get("user_id"):
            report_ids = {str(item.get("evidence_id")) for item in report.get("skill_evidence", [])}
            if report_ids - known_ids:
                hydrated = update_tree_from_report(hydrated, report)
                known_ids.update(report_ids)
    return hydrated


def _answer_turns(transcript: list[dict[str, Any]]) -> list[dict[str, str]]:
    question = ""
    turns: list[dict[str, str]] = []
    for item in transcript:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        if item.get("speaker") == "assistant":
            question = text
        elif item.get("speaker") == "candidate":
            turns.append({"question": question, "answer": text})
    return turns


def _build_evidence_detail(
    report: dict[str, Any], item: dict[str, Any], answer_turns: list[dict[str, str]]
) -> dict[str, Any]:
    skill = str(item["skill"])
    answer = next((turn for turn in answer_turns if _matches_skill(skill, turn["answer"])), None)
    answer = answer or (answer_turns[0] if answer_turns else {"question": "", "answer": ""})
    return {
        "evidence_id": str(item["evidence_id"]),
        "interview_id": str(report.get("interview_id", "")),
        "skill": skill,
        "question": answer["question"],
        "answer": answer["answer"],
        "knowledge_points": item.get("knowledge_points") or KNOWLEDGE_POINT_LIBRARY.get(skill, []),
    }


def _matches_skill(skill: str, answer: str) -> bool:
    keywords = {
        "ROS/ROS2": ("ROS", "ROS2"),
        "机械臂运动控制": ("机械臂", "运动控制", "轨迹", "插值"),
        "技术表达": (),
    }
    return any(keyword in answer for keyword in keywords.get(skill, ()))
