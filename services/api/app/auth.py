import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings
from app.storage import JsonStorage


class AuthService:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_salt() -> str:
        return secrets.token_hex(16)

    def ensure_demo_user(self) -> None:
        if self.storage.read_user("demo") is not None:
            return
        salt = self.generate_salt()
        self.storage.write_user(
            "demo",
            {
                "user_id": "demo",
                "username": "demo",
                "display_name": "演示用户",
                "password_hash": self.hash_password("demo123456", salt),
                "salt": salt,
            },
        )

    def login(self, username: str, password: str) -> dict | None:
        user = self.storage.read_user(username)
        if user is None:
            return None
        expected = self.hash_password(password, user["salt"])
        if not secrets.compare_digest(expected, user["password_hash"]):
            return None
        token = self.generate_token()
        self.storage.write_session(
            token,
            {
                "username": username,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return {"access_token": token, "user": user}

    def logout(self, token: str) -> bool:
        if self.storage.read_session(token) is None:
            return False
        self.storage.delete_session(token)
        return True

    def get_user_by_token(self, token: str) -> dict | None:
        session = self.storage.read_session(token)
        if session is None:
            return None
        return self.storage.read_user(session["username"])


def get_auth_service(settings: Settings = Depends(get_settings)) -> AuthService:
    service = AuthService(JsonStorage(settings.data_dir))
    service.ensure_demo_user()
    return service


def get_current_user(
    auth_service: AuthService = Depends(get_auth_service),
    authorization: str | None = Header(None),
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    user = auth_service.get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def get_optional_current_user(
    auth_service: AuthService = Depends(get_auth_service),
    authorization: str | None = Header(None),
) -> dict | None:
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    user = auth_service.get_user_by_token(authorization.removeprefix("Bearer "))
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user
