import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def isolate_local_env(monkeypatch):
    monkeypatch.setenv("REALTIME_MODE", "mock")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
