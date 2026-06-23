from datetime import datetime, timezone
from typing import Any


def empty_ability_tree(user_id: str) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "skills": [],
        "projects": [],
        "evidence": [],
        "target_skills": [],
        "edges": [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def update_tree_from_report(tree: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    updated = {**tree}
    skills = list(updated.get("skills", []))
    evidence = list(updated.get("evidence", []))
    edges = list(updated.get("edges", []))
    for item in report.get("skill_evidence", []):
        skill = item["skill"]
        evidence_id = item["evidence_id"]
        if skill not in skills:
            skills.append(skill)
        if evidence_id not in evidence:
            evidence.append(evidence_id)
        edge = {"from": evidence_id, "to": skill, "type": "supports"}
        if edge not in edges:
            edges.append(edge)
    for gap in report.get("target_gaps", []):
        if gap not in updated.get("target_skills", []):
            updated.setdefault("target_skills", []).append(gap)
    updated["skills"] = skills
    updated["evidence"] = evidence
    updated["edges"] = edges
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()
    return updated
