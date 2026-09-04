import pytest

from app.reporting import generate_analyzed_report, generate_report


def test_generate_report_contains_score_and_ability_updates():
    transcript = [
        {"speaker": "assistant", "text": "请介绍机械臂项目"},
        {"speaker": "candidate", "text": "我通过ROS2完成机械臂运动控制，并引入插值算法提升稳定性。"},
    ]

    report = generate_report("豆瓣酱", "int_1", transcript)

    assert report["score"]["average"] >= 3.0
    assert {"skill": "ROS/ROS2", "evidence_id": "int_1:ros"} in report["skill_evidence"]
    assert "MoveIt规划链路" in report["target_gaps"]


def test_duplicate_candidate_answers_do_not_increase_deterministic_score():
    answer = "通过ROS2实现机械臂。"
    single = generate_report(
        "demo",
        "iv_single",
        [{"speaker": "candidate", "text": answer}],
    )
    repeated = generate_report(
        "demo",
        "iv_repeat",
        [
            {"speaker": "candidate", "text": answer},
            {"speaker": "candidate", "text": answer},
        ],
    )

    assert repeated["score"]["average"] == single["score"]["average"]
    assert [item["skill"] for item in repeated["skill_evidence"]] == [
        item["skill"] for item in single["skill_evidence"]
    ]


@pytest.mark.asyncio
async def test_analyzed_report_uses_structured_text_model_result():
    class FakeTextClient:
        async def analyze_report(self, prompt: str) -> str:
            assert "ROS2" in prompt
            return (
                '{"summary":"回答有项目证据。","strengths":["能说明技术方案"],'
                '"target_gaps":["控制器参数整定"],"next_practice_plan":["补充量化结果"],'
                '"score":{"average":4.2}}'
            )

    report = await generate_analyzed_report(
        "demo",
        "int_2",
        [{"speaker": "candidate", "text": "我使用 ROS2。"}],
        text_client=FakeTextClient(),
    )

    assert report["analysis_mode"] == "bailian_text"
    assert report["summary"] == "回答有项目证据。"
    assert report["score"]["average"] == 4.2
