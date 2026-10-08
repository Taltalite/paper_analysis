from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from paper_analysis.adapters.storage.job_store import LocalFilesystemJobStore
from paper_analysis.adapters.storage.local_fs import LocalFilesystemArtifactStorage
from paper_analysis.services import build_default_analysis_service
from paper_analysis.services.artifact_service import ArtifactService
from paper_analysis.services.report_jobs import ProcessJobExecutor
from paper_analysis.services.job_service import JobService


_DATA_ROOT = Path(".data")
_JOBS_ROOT = _DATA_ROOT / "jobs"
_job_executor = ProcessJobExecutor()


@lru_cache
def get_job_service() -> JobService:
    # 健康检查、OpenAPI 和问答接口不应因文本模型配置在 import 阶段失败。
    # 分析请求首次到达时才装配默认 LLM/runtime。
    return JobService(
        job_store=LocalFilesystemJobStore(base_dir=_JOBS_ROOT / "store"),
        artifact_service=ArtifactService(storage=LocalFilesystemArtifactStorage()),
        # 默认主管仅管理状态；模型和解析器在 worker 内构建。
        analysis_service=None,
        workspace_root=_JOBS_ROOT / "workspace",
    )


def get_job_executor() -> ProcessJobExecutor:
    return _job_executor
