from app.ability_tree import empty_ability_tree, update_tree_from_report


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
