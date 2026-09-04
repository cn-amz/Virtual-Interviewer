import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader

from app.models import (
    JobDescription,
    JobDescriptionDocument,
    JobDescriptionAnalysis,
    ProfileSummary,
    ResumeDocument,
    SessionProfile,
)

INTERVIEW_PROFILE_DIR = "interview_profiles"
INTERVIEW_JOB_DESCRIPTION_DIR = "interview_job_descriptions"
RESUME_EXTENSIONS = {".pdf", ".doc", ".docx"}
MAX_RESUME_BYTES = 15 * 1024 * 1024
MAX_RESUME_CONTEXT_CHARS = 12_000


class ProfileLoader:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def list_profiles(self) -> list[str]:
        profile_dir = self.data_dir / INTERVIEW_PROFILE_DIR
        if not profile_dir.exists():
            return []
        return sorted(path.name for path in profile_dir.iterdir() if path.is_dir())

    def load_profile_summary(self, profile_id: str) -> ProfileSummary:
        profile_path = self.data_dir / INTERVIEW_PROFILE_DIR / profile_id / "profile.json"
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
        jd_path = self.get_job_description_path(jd_id)
        content = jd_path.read_text(encoding="utf-8")
        title = self._job_description_title(content, jd_path.stem)
        return JobDescription(jd_id=jd_id, title=title, content=content)

    def list_job_description_documents(self) -> list[JobDescriptionDocument]:
        jd_root = self.data_dir / INTERVIEW_JOB_DESCRIPTION_DIR
        if not jd_root.exists():
            return []
        documents: list[JobDescriptionDocument] = []
        for path in sorted(jd_root.glob("*.md"), key=lambda item: item.name.lower()):
            content = path.read_text(encoding="utf-8")
            title = self._job_description_title(content, path.stem)
            documents.append(
                JobDescriptionDocument(
                    jd_id=path.stem,
                    name=path.name,
                    title=title,
                    size=path.stat().st_size,
                    analysis_ready=self.get_job_description_analysis(path.stem) is not None,
                )
            )
        return documents

    def get_job_description_path(self, jd_id: str) -> Path:
        if not jd_id or Path(jd_id).name != jd_id:
            raise FileNotFoundError(jd_id)
        path = (self.data_dir / INTERVIEW_JOB_DESCRIPTION_DIR / f"{jd_id}.md").resolve()
        root = (self.data_dir / INTERVIEW_JOB_DESCRIPTION_DIR).resolve()
        if path.parent != root or not path.is_file():
            raise FileNotFoundError(jd_id)
        return path

    def save_job_description(self, filename: str, content: bytes) -> JobDescriptionDocument:
        name = Path(filename or "").name
        if name != filename or Path(name).suffix.lower() != ".md":
            raise ValueError("Job descriptions must be Markdown files")
        if not content:
            raise ValueError("Job description cannot be empty")
        jd_root = self.data_dir / INTERVIEW_JOB_DESCRIPTION_DIR
        jd_root.mkdir(parents=True, exist_ok=True)
        path = jd_root / name
        path.write_bytes(content)
        analysis_path = jd_root / f"{path.stem}.analysis.json"
        if analysis_path.exists():
            analysis_path.unlink()
        title = self._job_description_title(content.decode("utf-8"), path.stem)
        return JobDescriptionDocument(
            jd_id=path.stem,
            name=path.name,
            title=title,
            size=len(content),
        )

    def save_job_description_text(self, title: str, content: str) -> JobDescriptionDocument:
        body = content.strip()
        if not body:
            raise ValueError("Job description cannot be empty")
        clean_title = title.strip() or self._job_description_title(body, "未命名岗位")
        safe_stem = re.sub(r'[<>:"/\\|?*]+', "-", clean_title).strip(" .") or "未命名岗位"
        first_line = body.lstrip().splitlines()[0].strip()
        if not first_line.startswith("# "):
            body = f"# {clean_title}\n\n{body}"
        return self.save_job_description(f"{safe_stem}.md", f"{body.rstrip()}\n".encode("utf-8"))

    def get_job_description_analysis(self, jd_id: str) -> JobDescriptionAnalysis | None:
        self.get_job_description_path(jd_id)
        path = self.data_dir / INTERVIEW_JOB_DESCRIPTION_DIR / f"{jd_id}.analysis.json"
        if not path.is_file():
            return None
        try:
            return JobDescriptionAnalysis.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return None

    def save_job_description_analysis(self, jd_id: str, analysis: dict) -> JobDescriptionAnalysis:
        self.get_job_description_path(jd_id)
        validated = JobDescriptionAnalysis.model_validate(analysis)
        path = self.data_dir / INTERVIEW_JOB_DESCRIPTION_DIR / f"{jd_id}.analysis.json"
        path.write_text(validated.model_dump_json(indent=2), encoding="utf-8")
        return validated

    @staticmethod
    def _job_description_title(content: str, fallback: str) -> str:
        title = content.splitlines()[0].lstrip("# ").strip() if content else fallback
        return title.removeprefix("目标岗位：").removeprefix("目标岗位:").strip() or fallback

    def load_session_profile(self, profile_id: str, jd_id: str) -> SessionProfile:
        profile_root = self.data_dir / INTERVIEW_PROFILE_DIR / profile_id
        prompt = (profile_root / "prompt.txt").read_text(encoding="utf-8")
        qa_bank = (profile_root / "qa_bank.md").read_text(encoding="utf-8")
        return SessionProfile(
            profile=self.load_profile_summary(profile_id),
            job_description=self.load_job_description(jd_id),
            prompt=prompt,
            qa_bank=qa_bank,
        )

    def list_resume_documents(self, profile_id: str) -> list[ResumeDocument]:
        profile_root = self._profile_root(profile_id)
        if not profile_root.exists():
            return []
        return [
            ResumeDocument(
                name=path.name,
                format=path.suffix.lower().lstrip("."),
                size=path.stat().st_size,
            )
            for path in sorted(profile_root.iterdir(), key=lambda item: item.name.lower())
            if path.is_file() and path.suffix.lower() in RESUME_EXTENSIONS
        ]

    def get_resume_path(self, profile_id: str, resume_name: str) -> Path:
        profile_root = self._profile_root(profile_id)
        candidate = (profile_root / resume_name).resolve()
        if candidate.parent != profile_root.resolve() or candidate.suffix.lower() not in RESUME_EXTENSIONS:
            raise FileNotFoundError(resume_name)
        if not candidate.is_file():
            raise FileNotFoundError(resume_name)
        return candidate

    def load_resume_text(self, profile_id: str, resume_name: str) -> str:
        path = self.get_resume_path(profile_id, resume_name)
        if path.suffix.lower() == ".pdf":
            text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        elif path.suffix.lower() == ".docx":
            with ZipFile(path) as document:
                root = ET.fromstring(document.read("word/document.xml"))
            text = "".join(node.text or "" for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
        else:
            raise ValueError("Selected .doc resume cannot be used as interview context. Please upload PDF or DOCX.")
        normalized = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not normalized:
            raise ValueError("Selected resume contains no extractable text.")
        return normalized[:MAX_RESUME_CONTEXT_CHARS]

    def save_resume(self, profile_id: str, resume_name: str, content: bytes) -> ResumeDocument:
        name = Path(resume_name or "").name
        if name != resume_name or Path(name).suffix.lower() not in RESUME_EXTENSIONS:
            raise ValueError("Only PDF, DOC, and DOCX resumes are supported")
        if len(content) > MAX_RESUME_BYTES:
            raise ValueError("Resume file is too large")
        profile_root = self._profile_root(profile_id)
        profile_root.mkdir(parents=True, exist_ok=True)
        profile_path = profile_root / "profile.json"
        if not profile_path.exists():
            profile_path.write_text(
                json.dumps(
                    {"profile_id": profile_id, "name": profile_id, "skills": {}, "projects": []},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        (profile_root / name).write_bytes(content)
        return ResumeDocument(name=name, format=Path(name).suffix[1:].lower(), size=len(content))

    def _profile_root(self, profile_id: str) -> Path:
        if not profile_id or Path(profile_id).name != profile_id:
            raise FileNotFoundError(profile_id)
        return self.data_dir / INTERVIEW_PROFILE_DIR / profile_id
