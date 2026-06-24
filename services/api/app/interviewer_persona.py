from dataclasses import dataclass, field


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
    "warmup": "先做一分钟自我介绍，并点出你最匹配机械臂运控算法工程师的项目？",
    "resume_overview": "这个项目里你本人负责的核心模块是什么？",
    "project_deep_dive": "你引入插值算法前后的稳定性指标分别是多少？",
    "fundamentals": "轨迹规划和底层控制之间的接口你怎么定义？",
    "pressure_followup": "如果上线后机械臂出现抖动，你第一步查哪个信号？",
    "candidate_questions": "你想反问团队的业务场景还是技术栈？",
    "summary": "最后补充一个你认为最能证明岗位匹配度的证据？",
}


@dataclass(frozen=True)
class InterviewContext:
    candidate_name: str = "豆瓣酱"
    target_role: str = "机械臂运控算法工程师"
    resume_projects: tuple[str, ...] = ("ROS2机械臂运动控制",)
    resume_skills: tuple[str, ...] = ("ROS2", "机械臂运动控制", "轨迹规划", "插值算法")


@dataclass
class LocalTextInterviewer:
    context: InterviewContext = field(default_factory=InterviewContext)
    turn_index: int = 0

    def initial_question(self) -> str:
        project_hint = self._first_project()
        return (
            f"我们先从自我介绍开始。请用一分钟说明你的背景，"
            f"以及{project_hint}为什么匹配{self.context.target_role}？"
        )

    def next_question(self, last_answer: str) -> str:
        self.turn_index += 1
        answer = last_answer.strip()
        if self.turn_index == 1:
            return "你刚才提到的项目里，你本人负责的核心模块和接口边界是什么？"
        if _looks_vague(answer):
            return "这个回答还比较泛，请给出一个可量化指标或实测数据？"
        if _mentions_any(answer, ("ROS", "ROS2", "MoveIt", "Gazebo")):
            return "ROS2节点、控制器和运动规划模块之间的数据流怎么走？"
        if _mentions_any(answer, ("插值", "轨迹", "平滑", "抖动", "稳定")):
            return "轨迹平滑前后，你用哪个指标证明抖动确实下降了？"
        if _mentions_any(answer, ("标定", "视觉", "相机", "手眼")):
            return "手眼标定误差会怎样传导到末端控制精度？"
        if self.turn_index == 2:
            return f"简历里提到{self._first_project()}，你做过最关键的一次工程取舍是什么？"
        if self.turn_index == 3:
            return "如果实机验证失败，你会先排查通信、控制参数还是轨迹规划？"
        return "请补充一个最能证明你岗位匹配度的工程证据？"

    def _first_project(self) -> str:
        keywords = ("机器人", "机械臂", "ROS", "ROS2", "运动控制", "轨迹", "抓取", "MoveIt", "Gazebo")
        for project in self.context.resume_projects:
            if _mentions_any(project, keywords):
                return project
        return self.context.resume_projects[0] if self.context.resume_projects else "你的核心机器人项目"


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


def _mentions_any(answer: str, keywords: tuple[str, ...]) -> bool:
    lowered = answer.lower()
    return any(keyword.lower() in lowered for keyword in keywords)
