from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Virtual Interviewer API"
    app_storage_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / "data"
    )
    dashscope_api_key: str | None = Field(default=None, alias="DASHSCOPE_API_KEY")
    bailian_realtime_model: str = "qwen3.5-omni-plus-realtime"
    bailian_realtime_url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
    text_mode: str = "local"
    bailian_text_model: str = "qwen3.6-plus"
    bailian_text_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    minicpm_realtime_url: str = "wss://127.0.0.1:8006"
    realtime_mode: str = "mock"

    @property
    def data_dir(self) -> Path:
        return self.app_storage_dir.resolve()

    @property
    def minicpm_status_url(self) -> str:
        parts = urlsplit(self.minicpm_realtime_url)
        scheme = {"wss": "https", "ws": "http"}.get(parts.scheme, "http")
        path = f"{parts.path.rstrip('/')}/status"
        return urlunsplit((scheme, parts.netloc, path, "", ""))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
