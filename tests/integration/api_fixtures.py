"""API 测试使用独立报告仓库，避免触碰本地运行服务的任务和主管锁。"""
from pathlib import Path

from fastapi import FastAPI

from paper_analysis.adapters.storage.job_store import LocalFilesystemJobStore
from paper_analysis.adapters.storage.local_fs import LocalFilesystemArtifactStorage
from paper_analysis.api.deps import get_job_executor, get_job_service
from paper_analysis.services.artifact_service import ArtifactService
from paper_analysis.services.job_service import JobService
from paper_analysis.services.report_jobs import ProcessJobExecutor


def isolate_report_jobs(app: FastAPI, root: Path) -> None:
    service = JobService(
        job_store=LocalFilesystemJobStore(base_dir=root / "store"),
        artifact_service=ArtifactService(storage=LocalFilesystemArtifactStorage()),
        analysis_service=None,
        workspace_root=root / "workspace",
    )
    executor = ProcessJobExecutor()
    app.dependency_overrides[get_job_service] = lambda: service
    app.dependency_overrides[get_job_executor] = lambda: executor
