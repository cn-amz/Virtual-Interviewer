from fastapi import APIRouter

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    return {"status": "ok"}
