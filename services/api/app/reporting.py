from __future__ import annotations

import json
import re

from app.scoring import score_answer


def _parse_json_object(content: str) -> dict:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Report analysis must be a JSON object")
    return data


def generate_report(user_id: str, interview_id: str, transcript: list[dict[str, str]]) -> dict:
    candidate_answers = _distinct_candidate_answers(transcript)
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
        "analysis_mode": "deterministic",
    }


def _distinct_candidate_answers(transcript: list[dict[str, str]]) -> list[str]:
    answers: list[str] = []
    seen: set[str] = set()
    for item in transcript:
        if item.get("speaker") != "candidate":
            continue
        text = str(item.get("text", "")).strip()
        normalized = re.sub(r"[\W_]+", "", text).lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        answers.append(text)
    return answers


async def generate_analyzed_report(
    user_id: str,
    interview_id: str,
    transcript: list[dict[str, str]],
    *,
    text_client=None,
) -> dict:
    base = generate_report(user_id, interview_id, transcript)
    if text_client is None:
        return base

    prompt = (
        "请分析下面这次机械臂运控算法工程师模拟面试，并只返回 JSON，不要 Markdown。\n"
        "JSON 必须包含 summary（字符串）、strengths（字符串数组）、target_gaps（字符串数组）、"
        "next_practice_plan（字符串数组）、score（对象，包含 average 数字）。\n"
        "评分必须基于候选人的回答证据，不要凭空补充简历内容。\n"
        f"面试文本：{json.dumps(transcript, ensure_ascii=False)}"
    )
    try:
        data = _parse_json_object(await text_client.analyze_report(prompt))
        if isinstance(data.get("summary"), str) and data["summary"].strip():
            base["summary"] = data["summary"].strip()
        if isinstance(data.get("strengths"), list):
            base["strengths"] = [str(item) for item in data["strengths"] if str(item).strip()]
        if isinstance(data.get("target_gaps"), list):
            base["target_gaps"] = [str(item) for item in data["target_gaps"] if str(item).strip()]
        if isinstance(data.get("next_practice_plan"), list):
            base["next_practice_plan"] = [
                str(item) for item in data["next_practice_plan"] if str(item).strip()
            ]
        score_data = data.get("score")
        if isinstance(score_data, dict) and isinstance(score_data.get("average"), (int, float)):
            base["score"] = {**base["score"], **score_data}
            base["score"]["average"] = float(score_data["average"])
        base["analysis_mode"] = "bailian_text"
    except Exception as exc:
        base["analysis_mode"] = "deterministic_fallback"
        base["analysis_error"] = type(exc).__name__
    return base
