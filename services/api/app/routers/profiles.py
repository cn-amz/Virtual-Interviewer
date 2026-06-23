from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models import SessionProfile
from app.profile_loader import ProfileLoader

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def get_loader(settings: Settings = Depends(get_settings)) -> ProfileLoader:
    return ProfileLoader(settings.data_dir)


@router.get("")
def list_profiles(loader: ProfileLoader = Depends(get_loader)) -> dict[str, list[str]]:
    return {"profiles": loader.list_profiles()}


@router.get("/{profile_id}/session-profile", response_model=SessionProfile)
def get_session_profile(
    profile_id: str,
    jd_id: str = "mechanical-arm-motion-control-algorithm-engineer",
    loader: ProfileLoader = Depends(get_loader),
) -> SessionProfile:
    return loader.load_session_profile(profile_id, jd_id)
