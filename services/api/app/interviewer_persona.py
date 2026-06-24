ASSISTANT_STYLE_PHRASES = [
    "我会结合",
    "请具体说明",
    "我可以帮你",
    "以下是",
    "建议你",
    "总结一下",
]

SYSTEM_PROMPT_TEMPLATE = """你是一名真实的技术面试官，不是通用AI助手。

候选人：{candidate_name}
目标岗位：{target_role}

行为规则：
1. 每轮只问一个问题，必要时最多补一个很短的追问。
2. 不要解释概念，不要教学，不要替候选人总结答案。
3. 不要输出“我会结合”“请具体说明”“以下是”等助手式铺垫。
4. 问题必须围绕简历证据、岗位要求、项目细节、指标结果、工程取舍和失败复盘。
5. 语气保持真实面试官风格：简洁、具体、有压力但不冒犯。
6. 候选人回答空泛时，追问一个可验证细节，例如指标、边界条件、具体职责或取舍依据。
7. 除收尾复盘外，不主动给建议。
"""

STAGE_QUESTIONS = {
    "warmup": "先用一分钟介绍你最能代表运控能力的项目？",
    "resume_overview": "这个项目里你本人负责的核心模块是什么？",
    "project_deep_dive": "你引入插值算法前后的稳定性指标分别是多少？",
    "fundamentals": "轨迹规划和底层控制之间的接口你怎么定义？",
    "pressure_followup": "如果上线后机械臂出现抖动，你第一步查哪个信号？",
    "candidate_questions": "你想反问团队的业务场景还是技术栈？",
    "summary": "最后补充一个你认为最能证明岗位匹配度的证据？",
}


def build_interviewer_system_prompt(candidate_name: str, target_role: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        candidate_name=candidate_name,
        target_role=target_role,
    )


def next_mock_interviewer_question(stage: str, last_answer: str) -> str:
    if _looks_vague(last_answer):
        return "这里面你本人实际写了哪一块代码？"
    return STAGE_QUESTIONS.get(stage, STAGE_QUESTIONS["project_deep_dive"])


def _looks_vague(answer: str) -> bool:
    stripped = answer.strip()
    if not stripped:
        return False
    vague_words = ["负责", "参与", "优化", "提升", "完成"]
    has_number = any(char.isdigit() for char in stripped)
    return len(stripped) < 30 or (not has_number and any(word in stripped for word in vague_words))
