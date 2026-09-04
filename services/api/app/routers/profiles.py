from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.models import ResumeDocument, SessionProfile
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


@router.get("/{profile_id}/resumes", response_model=list[ResumeDocument])
def list_resumes(profile_id: str, loader: ProfileLoader = Depends(get_loader)) -> list[ResumeDocument]:
    return loader.list_resume_documents(profile_id)


@router.get("/{profile_id}/resumes/{resume_name:path}")
def get_resume(
    profile_id: str,
    resume_name: str,
    loader: ProfileLoader = Depends(get_loader),
) -> FileResponse:
    try:
        path = loader.get_resume_path(profile_id, resume_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Resume not found") from exc
    return FileResponse(path, filename=path.name, content_disposition_type="inline")


@router.post("/{profile_id}/resumes", response_model=ResumeDocument)
async def upload_resume(
    profile_id: str,
    file: UploadFile = File(...),
    loader: ProfileLoader = Depends(get_loader),
    _current_user: dict = Depends(get_current_user),
) -> ResumeDocument:
    try:
        return loader.save_resume(profile_id, file.filename or "", await file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
