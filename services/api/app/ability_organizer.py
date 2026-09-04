from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from copy import deepcopy
from typing import Any


TYPE_BY_SKILL = {
    "ROS/ROS2": "技术基础",
    "机械臂运动控制": "运动控制",
    "技术表达": "项目表达",
}


def normalize_question(value: str) -> str:
    """Create a stable key for exact or near-exact repeated questions."""
    text = re.sub(r"[\s\u3000]+", "", str(value).strip().lower())
    return re.sub(r"[，。！？、；：:,.!?;\"'“”‘’（）()\[\]{}]", "", text)


def question_id(value: str) -> str:
    digest = hashlib.sha1(normalize_question(value).encode("utf-8")).hexdigest()[:10]
    return f"question-{digest}"


def _point_key(point: Any) -> str:
    if isinstance(point, str):
        return point.strip()
    return str(point.get("title", "")).strip() if isinstance(point, dict) else ""


def _question_type(detail: dict[str, Any]) -> str:
    return TYPE_BY_SKILL.get(str(detail.get("skill", "")), "项目经历")


def _new_group(canonical_question: str) -> dict[str, Any]:
    return {
        "question_id": question_id(canonical_question),
        "canonical_question": canonical_question,
        "types": [],
        "skills": [],
        "evidence_ids": [],
        "knowledge_points": [],
    }


def _append_group_detail(group: dict[str, Any], detail: dict[str, Any], branch_type: str | None = None) -> None:
    detail_type = branch_type or _question_type(detail)
    if detail_type not in group["types"]:
        group["types"].append(detail_type)
    skill = str(detail.get("skill", "")).strip()
    if skill and skill not in group["skills"]:
        group["skills"].append(skill)
    evidence_id = str(detail.get("evidence_id", "")).strip()
    if evidence_id and evidence_id not in group["evidence_ids"]:
        group["evidence_ids"].append(evidence_id)
    known_points = {_point_key(item) for item in group["knowledge_points"]}
    for point in detail.get("knowledge_points", []):
        title = _point_key(point)
        if title and title not in known_points:
            group["knowledge_points"].append(point)
            known_points.add(title)


def deterministic_organize(tree: dict[str, Any]) -> dict[str, Any]:
    """Build the usable hierarchy without a network call.

    ponytail: exact normalized questions are merged locally; semantic paraphrase
    merging is delegated to the optional text model and falls back safely.
    """
    updated = deepcopy(tree)
    details = [item for item in updated.get("evidence_details", []) if item.get("evidence_id")]
    groups_by_key: dict[str, dict[str, Any]] = {}
    for detail in details:
        question = str(detail.get("question", "")).strip() or f"{detail.get('skill', '未分类')}相关问题"
        key = normalize_question(question) or f"skill:{detail.get('skill', '')}"
        group = groups_by_key.setdefault(key, _new_group(question))
        _append_group_detail(group, detail)

    groups = list(groups_by_key.values())
    branches = _branches_for_groups(groups)
    updated["question_groups"] = groups
    updated["type_branches"] = branches
    updated["organization_mode"] = "deterministic_fallback"
    updated.pop("organization_error", None)
    return updated


def _branches_for_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    branch_ids: dict[str, list[str]] = defaultdict(list)
    for group in groups:
        for branch_type in group.get("types", []) or ["项目经历"]:
            if group["question_id"] not in branch_ids[branch_type]:
                branch_ids[branch_type].append(group["question_id"])
    return [
        {"type": branch_type, "question_ids": ids}
        for branch_type, ids in branch_ids.items()
    ]


def _prompt(tree: dict[str, Any]) -> str:
    evidence = [
        {
            "evidence_id": item.get("evidence_id"),
            "skill": item.get("skill"),
            "question": item.get("question"),
            "answer": item.get("answer"),
        }
        for item in tree.get("evidence_details", [])
    ]
    return (
        "请整理面试能力树，只输出 JSON，不要 Markdown。将语义相同或只是措辞略有不同的问题合并为一个问题组，"
        "保留每个 evidence_id 且每个 evidence_id 必须且只能出现一次。按问题主题建立类型主干。"
        "JSON 格式必须是：{\"branches\":[{\"type\":\"类型\",\"question_groups\":["
        "{\"canonical_question\":\"合并后的问题\",\"evidence_ids\":[\"原 evidence_id\"]}]}]}。"
        "只能使用输入中的 evidence_id，不要编造问题或证据。\n输入："
        + json.dumps(evidence, ensure_ascii=False)
    )


def _parse_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    value = json.loads(text)
    if not isinstance(value, dict) or not isinstance(value.get("branches"), list):
        raise ValueError("model response must contain branches")
    return value


def _apply_model_result(tree: dict[str, Any], model_result: dict[str, Any]) -> dict[str, Any]:
    details = [item for item in tree.get("evidence_details", []) if item.get("evidence_id")]
    detail_by_id = {str(item["evidence_id"]): item for item in details}
    expected = set(detail_by_id)
    groups_by_key: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for branch in model_result["branches"]:
        if not isinstance(branch, dict) or not isinstance(branch.get("question_groups"), list):
            raise ValueError("invalid branch shape")
        branch_type = str(branch.get("type", "")).strip()
        if not branch_type:
            raise ValueError("branch type is empty")
        for raw_group in branch["question_groups"]:
            if not isinstance(raw_group, dict):
                raise ValueError("invalid question group shape")
            canonical = str(raw_group.get("canonical_question", "")).strip()
            ids = raw_group.get("evidence_ids")
            if not canonical or not isinstance(ids, list) or not ids:
                raise ValueError("invalid question group")
            key = normalize_question(canonical)
            group = groups_by_key.setdefault(key, _new_group(canonical))
            for evidence_id in ids:
                evidence_id = str(evidence_id)
                if evidence_id not in detail_by_id or evidence_id in seen:
                    raise ValueError("evidence ids must be known and unique")
                seen.add(evidence_id)
                _append_group_detail(group, detail_by_id[evidence_id], branch_type)
    if seen != expected:
        raise ValueError("model did not preserve every evidence id")
    updated = deepcopy(tree)
    groups = list(groups_by_key.values())
    updated["question_groups"] = groups
    updated["type_branches"] = _branches_for_groups(groups)
    updated["organization_mode"] = "bailian_text"
    updated.pop("organization_error", None)
    return updated


async def organize_with_text_model(tree: dict[str, Any], text_client: Any | None) -> dict[str, Any]:
    if text_client is None:
        return deterministic_organize(tree)
    try:
        raw = await text_client.organize_ability_tree(_prompt(tree))
        return _apply_model_result(tree, _parse_json(raw))
    except Exception as exc:
        fallback = deterministic_organize(tree)
        fallback["organization_error"] = str(exc)
        return fallback
