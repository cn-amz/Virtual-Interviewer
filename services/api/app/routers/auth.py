from fastapi import APIRouter, Depends, Header, HTTPException

from app.auth import AuthService, get_auth_service, get_current_user
from app.models import LoginRequest, LoginResponse, UserPublic

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> LoginResponse:
    result = auth_service.login(body.username, body.password)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    user = result["user"]
    return LoginResponse(
        access_token=result["access_token"],
        user=UserPublic(
            user_id=user["user_id"],
            username=user["username"],
            display_name=user["display_name"],
        ),
    )


@router.post("/logout")
def logout(
    auth_service: AuthService = Depends(get_auth_service),
    _user: dict = Depends(get_current_user),
    authorization: str = Header(...),
) -> dict:
    token = authorization.removeprefix("Bearer ")
    auth_service.logout(token)
    return {"status": "ok"}


@router.get("/me")
def me(user: dict = Depends(get_current_user)) -> UserPublic:
    return UserPublic(
        user_id=user["user_id"],
        username=user["username"],
        display_name=user["display_name"],
    )
