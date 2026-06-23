import json
from pathlib import Path
from typing import Any


class JsonStorage:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        (self.data_dir / "interviews").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "ability_graphs").mkdir(parents=True, exist_ok=True)

    def write_interview(self, interview_id: str, payload: dict[str, Any]) -> Path:
        path = self.data_dir / "interviews" / f"{interview_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def read_interview(self, interview_id: str) -> dict[str, Any]:
        path = self.data_dir / "interviews" / f"{interview_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def write_ability_tree(self, user_id: str, payload: dict[str, Any]) -> Path:
        path = self.data_dir / "ability_graphs" / f"{user_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
