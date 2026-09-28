from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from paper_analysis.api.routes.analysis import router as analysis_router
from paper_analysis.api.routes.health import router as health_router
from paper_analysis.api.routes.questions import router as questions_router
from paper_analysis.config import get_app_config
from paper_analysis.services.question_jobs import QuestionJobs
from paper_analysis.api.routes.questions import get_question_service


def create_app(*, qa_jobs: QuestionJobs | None = None) -> FastAPI:
    settings = get_app_config()
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        factory = app.dependency_overrides.get(get_question_service, get_question_service)
        jobs = qa_jobs or QuestionJobs(factory())
        app.state.qa_jobs = jobs
        await jobs.start()
        try:
            yield
        finally:
            await jobs.close()
    app = FastAPI(title="paper_analysis api", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(analysis_router)
    app.include_router(questions_router)
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
