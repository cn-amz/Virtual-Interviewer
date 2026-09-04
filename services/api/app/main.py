from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import ability_trees, auth, health, interviews, job_descriptions, profiles


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(profiles.router)
    app.include_router(job_descriptions.router)
    app.include_router(interviews.router)
    app.include_router(ability_trees.router)
    return app


app = create_app()
