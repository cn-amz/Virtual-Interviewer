from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.integrations.bailian.text_client import BailianTextClient, BailianTextConfig
from app.job_analysis import analyze_job_description
from app.models import JobDescriptionAnalysis, JobDescriptionDocument, JobDescriptionTextRequest
from app.profile_loader import ProfileLoader

router = APIRouter(prefix="/api/job-descriptions", tags=["job-descriptions"])


def get_loader(settings: Settings = Depends(get_settings)) -> ProfileLoader:
    return ProfileLoader(settings.data_dir)


@router.get("", response_model=list[JobDescriptionDocument])
def list_job_descriptions(
    loader: ProfileLoader = Depends(get_loader),
) -> list[JobDescriptionDocument]:
    return loader.list_job_description_documents()


@router.get("/{jd_id}/file")
def get_job_description(
    jd_id: str,
    loader: ProfileLoader = Depends(get_loader),
) -> FileResponse:
    try:
        path = loader.get_job_description_path(jd_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job description not found") from exc
    return FileResponse(
        path,
        filename=path.name,
        media_type="text/markdown; charset=utf-8",
        content_disposition_type="inline",
    )


@router.post("", response_model=JobDescriptionDocument)
async def upload_job_description(
    file: UploadFile = File(...),
    loader: ProfileLoader = Depends(get_loader),
    _current_user: dict = Depends(get_current_user),
) -> JobDescriptionDocument:
    try:
        return loader.save_job_description(file.filename or "", await file.read())
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{jd_id}/analysis", response_model=JobDescriptionAnalysis)
def get_job_description_analysis(
    jd_id: str,
    loader: ProfileLoader = Depends(get_loader),
    _current_user: dict = Depends(get_current_user),
) -> JobDescriptionAnalysis:
    analysis = loader.get_job_description_analysis(jd_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Job description analysis not found")
    return analysis


@router.post("/{jd_id}/analyze", response_model=JobDescriptionAnalysis)
async def analyze_job_description_route(
    jd_id: str,
    settings: Settings = Depends(get_settings),
    loader: ProfileLoader = Depends(get_loader),
    _current_user: dict = Depends(get_current_user),
) -> JobDescriptionAnalysis:
    try:
        jd = loader.load_job_description(jd_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job description not found") from exc
    text_client = None
    if settings.text_mode == "bailian_text":
        text_client = BailianTextClient(
            BailianTextConfig(
                api_key=settings.dashscope_api_key,
                model=settings.bailian_text_model,
                base_url=settings.bailian_text_base_url,
            ),
            system_prompt="你是岗位方向分析器，只输出符合要求的 JSON。",
        )
    analysis = await analyze_job_description(jd.jd_id, jd.title, jd.content, text_client)
    return loader.save_job_description_analysis(jd_id, analysis.model_dump() if hasattr(analysis, "model_dump") else analysis)


@router.post("/text", response_model=JobDescriptionDocument)
def create_job_description_from_text(
    request: JobDescriptionTextRequest,
    loader: ProfileLoader = Depends(get_loader),
    _current_user: dict = Depends(get_current_user),
) -> JobDescriptionDocument:
    try:
        return loader.save_job_description_text(request.title, request.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
