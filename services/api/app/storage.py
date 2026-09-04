import json
from datetime import datetime
from pathlib import Path
from typing import Any


class JsonStorage:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        (self.data_dir / "interviews").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "ability_graphs").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "users").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "sessions").mkdir(parents=True, exist_ok=True)

    def write_interview(self, interview_id: str, payload: dict[str, Any]) -> Path:
        path = self.data_dir / "interviews" / f"{interview_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def read_interview(self, interview_id: str) -> dict[str, Any]:
        path = self.data_dir / "interviews" / f"{interview_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def list_interviews(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in sorted(
            (self.data_dir / "interviews").glob("*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not self._is_displayable_report(payload, path.stem):
                continue
            payload.setdefault("interview_id", path.stem)
            payload["created_at"] = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
            records.append(payload)
        return records

    @staticmethod
    def _is_displayable_report(payload: dict[str, Any], interview_id: str) -> bool:
        report = payload.get("report") or {}
        if not report or not interview_id.startswith("iv_"):
            return False
        transcript = report.get("transcript") or payload.get("transcript") or []
        return any(
            item.get("speaker") == "candidate" and str(item.get("text", "")).strip()
            for item in transcript
            if isinstance(item, dict)
        )

    def write_ability_tree(self, user_id: str, payload: dict[str, Any]) -> Path:
        path = self.data_dir / "ability_graphs" / f"{user_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def read_ability_tree(self, user_id: str) -> dict[str, Any] | None:
        path = self.data_dir / "ability_graphs" / f"{user_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def read_user(self, username: str) -> dict[str, Any] | None:
        path = self.data_dir / "users" / f"{username}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_user(self, username: str, payload: dict[str, Any]) -> Path:
        path = self.data_dir / "users" / f"{username}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def read_session(self, token: str) -> dict[str, Any] | None:
        path = self.data_dir / "sessions" / f"{token}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_session(self, token: str, payload: dict[str, Any]) -> Path:
        path = self.data_dir / "sessions" / f"{token}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def delete_session(self, token: str) -> None:
        path = self.data_dir / "sessions" / f"{token}.json"
        if path.exists():
            path.unlink()
