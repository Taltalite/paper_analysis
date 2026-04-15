from __future__ import annotations

from pathlib import Path

from paper_analysis.adapters.storage.job_store import LocalFilesystemJobStore
from paper_analysis.adapters.storage.local_fs import LocalFilesystemArtifactStorage
from paper_analysis.services import build_default_analysis_service
from paper_analysis.services.artifact_service import ArtifactService
from paper_analysis.services.job_service import JobService


_DATA_ROOT = Path(".data")
_JOBS_ROOT = _DATA_ROOT / "jobs"
_job_store = LocalFilesystemJobStore(base_dir=_JOBS_ROOT / "store")
_artifact_service = ArtifactService(storage=LocalFilesystemArtifactStorage())
_analysis_service = build_default_analysis_service()
_job_service = JobService(
    job_store=_job_store,
    artifact_service=_artifact_service,
    analysis_service=_analysis_service,
    workspace_root=_JOBS_ROOT / "workspace",
)


def get_job_service() -> JobService:
    return _job_service
