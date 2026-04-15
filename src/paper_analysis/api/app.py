from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from paper_analysis.api.routes.analysis import router as analysis_router
from paper_analysis.api.routes.health import router as health_router
from paper_analysis.config import get_app_config


def create_app() -> FastAPI:
    settings = get_app_config()
    app = FastAPI(title="paper_analysis api", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(analysis_router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    settings = get_app_config()
    uvicorn.run(
        "paper_analysis.api.app:app",
        host=settings.backend.host,
        port=settings.backend.port,
        reload=False,
    )
