from __future__ import annotations
import asyncio
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
        # 健康检查和分析 API 不应因为问答模型尚未配置而启动失败。
        # 没有显式注入队列时，问答依赖在第一次访问 /api/qa 时惰性创建。
        app.state.qa_jobs = qa_jobs
        app.state.qa_jobs_started = False
        app.state.qa_jobs_lock = asyncio.Lock()
        if qa_jobs is not None:
            await qa_jobs.start()
            app.state.qa_jobs_started = True
        from paper_analysis.api.deps import get_job_executor, get_job_service
        # 重启即恢复报告队列，不依赖下一次上传触发，也不在 API 进程构建模型。
        report_executor = app.dependency_overrides.get(get_job_executor, get_job_executor)()
        if hasattr(report_executor, "start"):
            report_service = app.dependency_overrides.get(get_job_service, get_job_service)()
            await report_executor.start(report_service)
        try:
            yield
        finally:
            if hasattr(report_executor, "close"):
                await report_executor.close()
            jobs = getattr(app.state, "qa_jobs", None)
            if jobs is not None and getattr(app.state, "qa_jobs_started", False):
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
