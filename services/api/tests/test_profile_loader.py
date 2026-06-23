from pathlib import Path

from app.profile_loader import ProfileLoader


def test_loader_finds_copied_profile():
    loader = ProfileLoader(Path("../../data").resolve())

    profiles = loader.list_profiles()

    assert "豆瓣酱" in profiles


def test_loader_builds_session_profile():
    loader = ProfileLoader(Path("../../data").resolve())

    session = loader.load_session_profile(
        "豆瓣酱",
        "mechanical-arm-motion-control-algorithm-engineer",
    )

    assert session.profile.name == "豆瓣酱"
    assert "Python" in session.profile.skills
    assert "机械臂" in session.job_description.content
    assert len(session.qa_bank) > 100
