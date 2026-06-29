from app.interviewer_persona import (
    ASSISTANT_STYLE_PHRASES,
    InterviewContext,
    LocalTextInterviewer,
    build_interviewer_system_prompt,
    next_mock_interviewer_question,
)


def test_system_prompt_restricts_assistant_style_and_teaching():
    prompt = build_interviewer_system_prompt(
        candidate_name="豆瓣酱",
        target_role="机械臂运控算法工程师",
    )

    assert "技术面试官" in prompt
    assert "不是通用 AI 助手" in prompt
    assert "不要解释概念" in prompt
    assert "每轮只问一个问题" in prompt
    assert "机械臂运控算法工程师" in prompt


def test_mock_interviewer_question_is_short_single_question():
    question = next_mock_interviewer_question(
        stage="project_deep_dive",
        last_answer="我通过ROS2完成机械臂运动控制，并引入插值算法提升稳定性。",
    )

    assert question.endswith("？")
    assert question.count("？") == 1
    assert len(question) <= 60
    assert not any(phrase in question for phrase in ASSISTANT_STYLE_PHRASES)


def test_mock_interviewer_question_changes_by_stage():
    warmup = next_mock_interviewer_question(stage="warmup", last_answer="")
    pressure = next_mock_interviewer_question(stage="pressure_followup", last_answer="项目上线后抖动变大。")

    assert warmup != pressure
    assert warmup.endswith("。")
    assert pressure.endswith("？")


def test_local_text_interviewer_starts_with_self_introduction():
    interviewer = LocalTextInterviewer(
        InterviewContext(
            candidate_name="豆瓣酱",
            target_role="机械臂运控算法工程师",
            resume_projects=("ROS2机械臂运动控制",),
            resume_skills=("ROS2", "轨迹规划"),
        )
    )

    question = interviewer.initial_question()

    assert "自我介绍" in question
    assert "机械臂运控算法工程师" in question
    assert question.endswith("。")


def test_local_text_interviewer_prefers_robotics_resume_project():
    interviewer = LocalTextInterviewer(
        InterviewContext(
            candidate_name="豆瓣酱",
            target_role="机械臂运控算法工程师",
            resume_projects=("船舶结构安全全国重点实验室", "实体机器人部署与验证"),
            resume_skills=("ROS2", "运动控制"),
        )
    )

    question = interviewer.initial_question()

    assert "实体机器人部署与验证" in question


def test_local_text_interviewer_adapts_to_answer_content():
    interviewer = LocalTextInterviewer(
        InterviewContext(
            candidate_name="豆瓣酱",
            target_role="机械臂运控算法工程师",
            resume_projects=("ROS2机械臂运动控制",),
            resume_skills=("ROS2", "轨迹规划"),
        )
    )

    first = interviewer.next_question("我做过ROS2机械臂运动控制项目。")
    second = interviewer.next_question("我负责优化轨迹稳定性。")

    assert first != second
    assert "本人负责" in first
    assert "指标" in second
