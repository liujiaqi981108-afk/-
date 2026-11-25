"""FastAPI application entry point mounting API, media workspaces, and Studio UI."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as studio_router
from app.config import STATIC_DIR, WORKSPACES_DIR


def create_app() -> FastAPI:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    application = FastAPI(
        title="9-Agent AI Short-Film Pre-Production & Storyboard Studio",
        description="Industrial T2I -> I2V Multi-Agent Short Video Studio Workbench",
        version="1.0.0",
    )

    application.include_router(studio_router)
    application.mount("/workspaces", StaticFiles(directory=str(WORKSPACES_DIR)), name="workspaces")
    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @application.get("/", include_in_schema=False)
    async def serve_studio_index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return application


app = create_app()
