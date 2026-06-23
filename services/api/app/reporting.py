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
