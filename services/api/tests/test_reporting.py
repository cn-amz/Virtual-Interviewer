from app.reporting import generate_report


def test_generate_report_contains_score_and_ability_updates():
    transcript = [
        {"speaker": "assistant", "text": "请介绍机械臂项目"},
        {"speaker": "candidate", "text": "我通过ROS2完成机械臂运动控制，并引入插值算法提升稳定性。"},
    ]

    report = generate_report("豆瓣酱", "int_1", transcript)

    assert report["score"]["average"] >= 3.0
    assert {"skill": "ROS/ROS2", "evidence_id": "int_1:ros"} in report["skill_evidence"]
    assert "MoveIt规划链路" in report["target_gaps"]
