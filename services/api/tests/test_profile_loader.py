import json
from pathlib import Path

from app.profile_loader import ProfileLoader


def write_session_fixture(data_dir: Path) -> None:
    profile_root = data_dir / "interview_profiles" / "豆瓣酱"
    profile_root.mkdir(parents=True)
    (profile_root / "profile.json").write_text(
        json.dumps(
            {
                "profile_id": "豆瓣酱",
                "name": "豆瓣酱",
                "skills": {"programming": ["Python"]},
                "projects": [{"name": "机械臂控制"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (profile_root / "prompt.txt").write_text("你是面试官。", encoding="utf-8")
    (profile_root / "qa_bank.md").write_text("机械臂问答" * 21, encoding="utf-8")
    jd_root = data_dir / "interview_job_descriptions"
    jd_root.mkdir()
    (jd_root / "mechanical-arm-motion-control-algorithm-engineer.md").write_text(
        "# 机械臂运控算法工程师\n\n熟悉 Python 与机械臂控制。",
        encoding="utf-8",
    )


def test_loader_finds_interview_profile(tmp_path):
    write_session_fixture(tmp_path)
    loader = ProfileLoader(tmp_path)

    profiles = loader.list_profiles()

    assert "豆瓣酱" in profiles


def test_loader_builds_session_profile(tmp_path):
    write_session_fixture(tmp_path)
    loader = ProfileLoader(tmp_path)

    session = loader.load_session_profile(
        "豆瓣酱",
        "mechanical-arm-motion-control-algorithm-engineer",
    )

    assert session.profile.name == "豆瓣酱"
    assert "Python" in session.profile.skills
    assert "机械臂" in session.job_description.content
    assert len(session.qa_bank) > 100


def test_loader_lists_only_resume_documents(tmp_path):
    profile_root = tmp_path / "interview_profiles" / "candidate"
    profile_root.mkdir(parents=True)
    (profile_root / "resume.pdf").write_bytes(b"pdf")
    (profile_root / "resume.docx").write_bytes(b"docx")
    (profile_root / "profile.json").write_text("{}", encoding="utf-8")
    (profile_root / "training.jsonl").write_text("private", encoding="utf-8")

    documents = ProfileLoader(tmp_path).list_resume_documents("candidate")

    assert [(item.name, item.format, item.size) for item in documents] == [
        ("resume.docx", "docx", 4),
        ("resume.pdf", "pdf", 3),
    ]


def test_loader_lists_and_resolves_job_descriptions(tmp_path):
    jd_root = tmp_path / "interview_job_descriptions"
    jd_root.mkdir()
    (jd_root / "robotics.md").write_text("# 机械臂运控算法工程师\n\n## 职责", encoding="utf-8")

    loader = ProfileLoader(tmp_path)
    documents = loader.list_job_description_documents()

    assert documents[0].jd_id == "robotics"
    assert documents[0].title == "机械臂运控算法工程师"
    assert loader.get_job_description_path("robotics").name == "robotics.md"


def test_loader_saves_pasted_job_description_as_markdown(tmp_path):
    loader = ProfileLoader(tmp_path)

    document = loader.save_job_description_text("机械臂运控算法工程师", "## 任职要求\n\n熟悉 ROS2")

    assert document.name == "机械臂运控算法工程师.md"
    content = (tmp_path / "interview_job_descriptions" / document.name).read_text(encoding="utf-8")
    assert content.startswith("# 机械臂运控算法工程师\n\n## 任职要求")


def test_loader_invalidates_stale_job_analysis_when_content_is_replaced(tmp_path):
    loader = ProfileLoader(tmp_path)
    document = loader.save_job_description_text("岗位", "原始内容")
    analysis_path = tmp_path / "interview_job_descriptions" / "岗位.analysis.json"
    analysis_path.write_text("{}", encoding="utf-8")

    loader.save_job_description_text("岗位", "新的岗位内容")

    assert not analysis_path.exists()
