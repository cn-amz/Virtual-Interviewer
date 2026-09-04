from app.ability_tree import empty_ability_tree, update_tree_from_report
from app.ability_tree_markdown import write_ability_tree_markdown


def test_update_tree_adds_supported_skill_and_gap():
    tree = empty_ability_tree("豆瓣酱")
    report = {
        "skill_evidence": [{"skill": "ROS/ROS2", "evidence_id": "int_1:ros"}],
        "target_gaps": ["MoveIt规划链路"],
    }

    updated = update_tree_from_report(tree, report)

    assert "ROS/ROS2" in updated["skills"]
    assert "int_1:ros" in updated["evidence"]
    assert {"from": "int_1:ros", "to": "ROS/ROS2", "type": "supports"} in updated["edges"]
    assert "MoveIt规划链路" in updated["target_skills"]


def test_markdown_tree_contains_obsidian_links(tmp_path):
    tree = update_tree_from_report(
        empty_ability_tree("demo"),
        {
            "skill_evidence": [{"skill": "ROS/ROS2", "evidence_id": "int_1:ros"}],
            "target_gaps": ["MoveIt规划链路"],
        },
    )

    index = write_ability_tree_markdown(tmp_path, "demo", tree)

    content = index.read_text(encoding="utf-8")
    assert "[[skills/skill-1]] ROS/ROS2" in content
    assert "[[targets/target-1]] MoveIt规划链路" in content
    assert (tmp_path / "ability_graphs" / "demo" / "evidence" / "evidence-1.md").exists()


def test_markdown_evidence_contains_question_answer_and_utf8_bom(tmp_path):
    tree = update_tree_from_report(
        empty_ability_tree("demo"),
        {
            "interview_id": "int_1",
            "transcript": [
                {"speaker": "assistant", "text": "请解释轨迹插值。"},
                {"speaker": "candidate", "text": "我会按控制周期做重采样。"},
            ],
            "skill_evidence": [{"skill": "机械臂运动控制", "evidence_id": "int_1:motion"}],
            "target_gaps": [],
        },
    )

    index = write_ability_tree_markdown(tmp_path, "demo", tree)
    evidence = index.parent / "evidence" / "evidence-1.md"

    assert "## 面试问题" in evidence.read_text(encoding="utf-8-sig")
    assert "请解释轨迹插值。" in evidence.read_text(encoding="utf-8-sig")
    assert evidence.read_bytes()[:3] == b"\xef\xbb\xbf"


def test_update_tree_keeps_question_answer_and_knowledge_points():
    tree = update_tree_from_report(
        empty_ability_tree("demo"),
        {
            "interview_id": "int_1",
            "transcript": [
                {"speaker": "assistant", "text": "请解释你的 ROS2 项目。"},
                {"speaker": "candidate", "text": "我负责 ROS2 节点通信和运动控制。"},
            ],
            "skill_evidence": [{"skill": "ROS/ROS2", "evidence_id": "int_1:ros"}],
            "target_gaps": [],
        },
    )

    detail = tree["evidence_details"][0]
    assert detail["question"] == "请解释你的 ROS2 项目。"
    assert detail["answer"].startswith("我负责 ROS2")
    assert detail["knowledge_points"][0]["title"] == "ROS2 通信、DDS 与 QoS"
