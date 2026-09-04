import pytest

from app.ability_organizer import deterministic_organize, organize_with_text_model
from app.ability_tree import empty_ability_tree, update_tree_from_report


def _tree_with_repeated_questions():
    tree = empty_ability_tree("demo")
    for interview_id, question in (("iv_1", "请介绍机械臂项目。"), ("iv_2", "请介绍机械臂项目")):
        tree = update_tree_from_report(
            tree,
            {
                "interview_id": interview_id,
                "transcript": [
                    {"speaker": "assistant", "text": question},
                    {"speaker": "candidate", "text": f"回答 {interview_id}"},
                ],
                "skill_evidence": [
                    {"skill": "机械臂运动控制", "evidence_id": f"{interview_id}:motion"}
                ],
            },
        )
    return tree


def test_deterministic_organizer_merges_repeated_question_and_keeps_evidence():
    organized = deterministic_organize(_tree_with_repeated_questions())

    assert len(organized["question_groups"]) == 1
    assert organized["question_groups"][0]["evidence_ids"] == ["iv_1:motion", "iv_2:motion"]
    assert organized["type_branches"] == [{"type": "运动控制", "question_ids": [organized["question_groups"][0]["question_id"]]}]


@pytest.mark.asyncio
async def test_invalid_model_result_falls_back_without_losing_evidence():
    class FakeTextClient:
        async def organize_ability_tree(self, prompt):
            return '{"branches": []}'

    organized = await organize_with_text_model(_tree_with_repeated_questions(), FakeTextClient())

    assert organized["organization_mode"] == "deterministic_fallback"
    assert set(organized["question_groups"][0]["evidence_ids"]) == {"iv_1:motion", "iv_2:motion"}
    assert organized["organization_error"]


@pytest.mark.asyncio
async def test_valid_model_result_merges_semantic_question_and_records_mode():
    tree = _tree_with_repeated_questions()

    class FakeTextClient:
        async def organize_ability_tree(self, prompt):
            return '{"branches":[{"type":"项目经历","question_groups":[{"canonical_question":"请介绍你的机械臂项目","evidence_ids":["iv_1:motion","iv_2:motion"]}]}]}'

    organized = await organize_with_text_model(tree, FakeTextClient())

    assert organized["organization_mode"] == "bailian_text"
    assert organized["question_groups"][0]["canonical_question"] == "请介绍你的机械臂项目"
    assert organized["type_branches"][0]["type"] == "项目经历"
