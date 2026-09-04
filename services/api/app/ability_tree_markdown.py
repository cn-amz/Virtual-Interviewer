from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _safe_title(value: Any) -> str:
    return str(value).replace("\n", " ").strip()


def _write(path: Path, content: str) -> None:
    # utf-8-sig keeps the file readable by Windows tools that guess ANSI encoding.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8-sig")


def _knowledge_entries(tree: dict[str, Any]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for detail in tree.get("evidence_details", []):
        for point in detail.get("knowledge_points", []):
            if isinstance(point, str):
                point = {"title": point, "summary": "", "obsidian_ref": ""}
            title = _safe_title(point.get("title", ""))
            if title and title not in seen:
                entries.append(
                    {
                        "title": title,
                        "summary": _safe_title(point.get("summary", "")),
                        "obsidian_ref": _safe_title(point.get("obsidian_ref", "")),
                    }
                )
                seen.add(title)
    return entries


def write_ability_tree_markdown(data_dir: Path, user_id: str, tree: dict[str, Any]) -> Path:
    """Materialize the JSON tree as an Obsidian-compatible, evidence-first vault."""
    root = data_dir / "ability_graphs" / user_id
    skills_dir = root / "skills"
    targets_dir = root / "targets"
    types_dir = root / "types"
    questions_dir = root / "questions"
    evidence_dir = root / "evidence"
    knowledge_dir = root / "knowledge"
    for directory in (skills_dir, targets_dir, types_dir, questions_dir, evidence_dir, knowledge_dir):
        directory.mkdir(parents=True, exist_ok=True)

    skills = [_safe_title(item) for item in tree.get("skills", [])]
    targets = [_safe_title(item) for item in tree.get("target_skills", [])]
    evidence = [_safe_title(item) for item in tree.get("evidence", [])]
    details = [item for item in tree.get("evidence_details", []) if item.get("evidence_id")]
    detail_by_id = {str(item["evidence_id"]): item for item in details}
    evidence_indexes = {item: index for index, item in enumerate(evidence, 1)}
    knowledge = _knowledge_entries(tree)
    knowledge_indexes = {item["title"]: index for index, item in enumerate(knowledge, 1)}
    groups = [item for item in tree.get("question_groups", []) if item.get("question_id")]
    group_by_id = {str(item["question_id"]): item for item in groups}
    branches = [item for item in tree.get("type_branches", []) if item.get("type")]

    for index, item in enumerate(knowledge, 1):
        _write(
            knowledge_dir / f"knowledge-{index}.md",
            "---\n"
            f"title: {item['title']}\n"
            "type: knowledge\n"
            "tags: [面试知识点, 能力树]\n"
            "---\n\n"
            f"# {item['title']}\n\n"
            f"{item['summary']}\n\n"
            f"主知识库参考：{item['obsidian_ref'] or '待补充'}\n",
        )

    for index, skill in enumerate(skills, 1):
        related = [
            (evidence_indexes[item["evidence_id"]], item)
            for item in details
            if item.get("skill") == skill and item.get("evidence_id") in evidence_indexes
        ]
        links = "\n".join(f"- [[../evidence/evidence-{evidence_index}]]" for evidence_index, _ in related)
        _write(
            skills_dir / f"skill-{index}.md",
            "---\n"
            f"title: {skill}\n"
            "type: skill\n"
            "tags: [能力树, 已形成能力]\n"
            "---\n\n"
            f"# {skill}\n\n"
            "## 面试证据\n"
            f"{links or '- 暂无具体面试证据'}\n",
        )

    for index, target in enumerate(targets, 1):
        _write(
            targets_dir / f"target-{index}.md",
            "---\n"
            f"title: {target}\n"
            "type: target\n"
            "tags: [能力树, 待提升]\n"
            "---\n\n"
            f"# {target}\n\n"
            "这是需要持续补齐的虚拟树枝。完成相关训练后，应在下一次面试中用真实回答验证。\n",
        )

    for index, evidence_id in enumerate(evidence, 1):
        detail = detail_by_id.get(evidence_id, {})
        point_links = []
        for point in detail.get("knowledge_points", []):
            title = _safe_title(point if isinstance(point, str) else point.get("title", ""))
            if title in knowledge_indexes:
                point_links.append(f"- [[../knowledge/knowledge-{knowledge_indexes[title]}]] {title}")
        _write(
            evidence_dir / f"evidence-{index}.md",
            "---\n"
            f"title: 面试证据 {index}\n"
            "type: evidence\n"
            f"interview_id: {detail.get('interview_id', '')}\n"
            f"skill: {detail.get('skill', '')}\n"
            "tags: [能力树, 面试证据]\n"
            "---\n\n"
            f"# 面试证据 {index}\n\n"
            "## 面试问题\n"
            f"> {detail.get('question', '历史记录未保存问题文本')}\n\n"
            "## 我的回答\n"
            f"> {detail.get('answer', '历史记录未保存回答文本')}\n\n"
            "## 相关知识点\n"
            f"{chr(10).join(point_links) or '- 暂无结构化知识点'}\n\n"
            "## 原始记录\n"
            f"面试 ID：`{detail.get('interview_id', '')}`\n",
        )

    for index, group in enumerate(groups, 1):
        evidence_links = []
        for evidence_id in group.get("evidence_ids", []):
            evidence_index = evidence_indexes.get(str(evidence_id))
            if evidence_index:
                evidence_links.append(
                    f"- [[../evidence/evidence-{evidence_index}]] "
                    f"{detail_by_id.get(str(evidence_id), {}).get('interview_id', '')}"
                )
        point_links = []
        for point in group.get("knowledge_points", []):
            title = _safe_title(point if isinstance(point, str) else point.get("title", ""))
            if title in knowledge_indexes:
                point_links.append(f"- [[../knowledge/knowledge-{knowledge_indexes[title]}]] {title}")
        _write(
            questions_dir / f"question-{index}.md",
            "---\n"
            f"title: {_safe_title(group.get('canonical_question', '面试问题'))}\n"
            "type: question-group\n"
            f"question_id: {group['question_id']}\n"
            f"types: [{', '.join(group.get('types', []))}]\n"
            "tags: [能力树, 合并问题]\n"
            "---\n\n"
            f"# {_safe_title(group.get('canonical_question', '面试问题'))}\n\n"
            f"问题类型：{'、'.join(group.get('types', [])) or '未分类'}\n\n"
            "## 多次回答证据\n"
            f"{chr(10).join(evidence_links) or '- 暂无证据'}\n\n"
            "## 相关知识点\n"
            f"{chr(10).join(point_links) or '- 暂无结构化知识点'}\n",
        )

    type_links: list[str] = []
    question_indexes = {str(group["question_id"]): index for index, group in enumerate(groups, 1)}
    for index, branch in enumerate(branches, 1):
        question_links = []
        for question_id in branch.get("question_ids", []):
            question_index = question_indexes.get(str(question_id))
            group = group_by_id.get(str(question_id), {})
            if question_index:
                question_links.append(
                    f"- [[../questions/question-{question_index}]] "
                    f"{_safe_title(group.get('canonical_question', '面试问题'))}"
                )
        _write(
            types_dir / f"type-{index}.md",
            "---\n"
            f"title: {_safe_title(branch['type'])}\n"
            "type: ability-type\n"
            "tags: [能力树, 类型主干]\n"
            "---\n\n"
            f"# {_safe_title(branch['type'])}\n\n"
            f"{chr(10).join(question_links) or '- 暂无合并问题'}\n",
        )
        type_links.append(f"- [[types/type-{index}]] {_safe_title(branch['type'])}")

    updated_at = tree.get("updated_at") or datetime.now(timezone.utc).isoformat()
    target_lines = [
        f"- [[targets/target-{index}]] {target}" for index, target in enumerate(targets, 1)
    ] or ["- 暂无待提升项"]
    evidence_lines = [
        f"- [[evidence/evidence-{index}]] {detail_by_id.get(item, {}).get('skill', item)}"
        for index, item in enumerate(evidence, 1)
    ] or ["- 暂无面试证据"]
    knowledge_lines = [
        f"- [[knowledge/knowledge-{index}]] {item['title']}"
        for index, item in enumerate(knowledge, 1)
    ] or ["- 暂无结构化知识点"]
    formed_skill_lines = [
        f"- [[skills/skill-{index}]] {skill}" for index, skill in enumerate(skills, 1)
    ] or ["- 暂无已形成能力"]
    index_lines = [
        "---",
        f"title: {user_id} 能力树",
        f"user_id: {user_id}",
        f"updated_at: {updated_at}",
        "tags: [能力树, 面试复盘]",
        "---",
        "",
        f"# {user_id} 能力树",
        "",
        "> [!info] 使用方式\n> 类型主干 → 合并问题 → 多次回答证据 → 相关知识点。相同问题只保留一个问题节点。",
        "",
        "## 类型主干",
        *(type_links or ["- 暂无类型化问题"]),
        "",
        "## 待提升虚拟树枝",
        *target_lines,
        "",
        "## 已形成能力",
        *formed_skill_lines,
        "",
        "## 面试证据总览",
        *evidence_lines,
        "",
        "## 知识点总览",
        *knowledge_lines,
        "",
        "## 数据来源",
        "- 原始问题与回答来自面试事件账本；JSON 是应用规范数据，Markdown 便于在 Obsidian 中浏览。",
        "- 主学习库 `knowledge-graph/` 保持独立，知识点笔记只保存关联入口，不复制主知识库内容。",
        "",
    ]
    index_path = root / "index.md"
    _write(index_path, "\n".join(index_lines))
    return index_path
