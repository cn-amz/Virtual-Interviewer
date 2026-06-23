import json
from pathlib import Path

from app.models import JobDescription, ProfileSummary, SessionProfile


class ProfileLoader:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def list_profiles(self) -> list[str]:
        profile_dir = self.data_dir / "profiles"
        if not profile_dir.exists():
            return []
        return sorted(path.name for path in profile_dir.iterdir() if path.is_dir())

    def load_profile_summary(self, profile_id: str) -> ProfileSummary:
        profile_path = self.data_dir / "profiles" / profile_id / "profile.json"
        data = json.loads(profile_path.read_text(encoding="utf-8"))
        skills: list[str] = []
        raw_skills = data.get("skills", {})
        if isinstance(raw_skills, dict):
            for values in raw_skills.values():
                if isinstance(values, list):
                    skills.extend(str(item) for item in values)
        projects = [
            str(project.get("name", "")).strip()
            for project in data.get("projects", [])
            if str(project.get("name", "")).strip()
        ]
        return ProfileSummary(
            profile_id=str(data.get("profile_id", profile_id)),
            name=str(data.get("name", profile_id)),
            skills=sorted(set(skills)),
            projects=projects,
        )

    def load_job_description(self, jd_id: str) -> JobDescription:
        jd_path = self.data_dir / "job_descriptions" / f"{jd_id}.md"
        content = jd_path.read_text(encoding="utf-8")
        title = content.splitlines()[0].lstrip("# ").strip()
        return JobDescription(jd_id=jd_id, title=title, content=content)

    def load_session_profile(self, profile_id: str, jd_id: str) -> SessionProfile:
        profile_root = self.data_dir / "profiles" / profile_id
        prompt = (profile_root / "prompt.txt").read_text(encoding="utf-8")
        qa_bank = (profile_root / "qa_bank.md").read_text(encoding="utf-8")
        return SessionProfile(
            profile=self.load_profile_summary(profile_id),
            job_description=self.load_job_description(jd_id),
            prompt=prompt,
            qa_bank=qa_bank,
        )
