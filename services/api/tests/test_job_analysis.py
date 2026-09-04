import pytest

from app.job_analysis import analyze_job_description, deterministic_job_analysis


def test_deterministic_job_analysis_distinguishes_motor_control_from_manipulator_role():
    motor = deterministic_job_analysis("motor", "运控算法工程师", "负责 FOC、PMSM、电机控制和 ARM/DSP 部署")
    arm = deterministic_job_analysis("arm", "算法工程师", "负责机械臂 MoveIt2、逆运动学、手眼标定和抓取")

    assert motor["role_direction"] == "电机与伺服控制"
    assert arm["role_direction"] == "机械臂规划、控制与操作"
    assert motor["role_direction"] != arm["role_direction"]


def test_manipulator_terms_win_over_generic_learning_keywords():
    analysis = deterministic_job_analysis(
        "机械臂运控算法工程师",
        "机械臂运控算法工程师",
        "机械臂运动控制、MoveIt、手眼标定和抓取，了解 VLA 与强化学习",
    )

    assert analysis["role_direction"] == "机械臂规划、控制与操作"


@pytest.mark.asyncio
async def test_job_analysis_accepts_valid_bailian_json():
    class FakeTextClient:
        async def analyze_job_description(self, prompt):
            assert "岗位名称可能与实际方向不一致" in prompt
            return '{"role_family":"机器人算法","role_direction":"机械臂规划","focus_points":["MoveIt"],"question_strategy":["追问指标"],"initial_prompt":"你是真实面试官。","source_keywords":["MoveIt"]}'

    analysis = await analyze_job_description("arm", "岗位", "MoveIt", FakeTextClient())

    assert analysis["analysis_mode"] == "bailian_text"
    assert analysis["role_direction"] == "机械臂规划"
    assert analysis["focus_points"] == ["MoveIt"]
    assert analysis["research_sources"]


@pytest.mark.asyncio
async def test_job_analysis_falls_back_when_model_json_is_invalid():
    class FakeTextClient:
        async def analyze_job_description(self, prompt):
            return "not json"

    analysis = await analyze_job_description("arm", "岗位", "机械臂", FakeTextClient())

    assert analysis["analysis_mode"] == "deterministic_fallback"
    assert analysis["analysis_error"] == "JSONDecodeError"
