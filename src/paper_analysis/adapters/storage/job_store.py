from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from paper_analysis.adapters.storage.base import JobStore
from paper_analysis.domain.schemas import AnalysisJob


class InMemoryJobStore(JobStore):
    def __init__(self) -> None:
        self._jobs: dict[UUID, AnalysisJob] = {}

    async def save(self, job: AnalysisJob) -> AnalysisJob:
        self._jobs[job.id] = job
        return job

    async def get(self, job_id: UUID) -> AnalysisJob:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise KeyError(f"Unknown job id: {job_id}") from exc


class LocalFilesystemJobStore(JobStore):
    def __init__(self, *, base_dir: Path) -> None:
        self._base_dir = base_dir

    async def save(self, job: AnalysisJob) -> AnalysisJob:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        path = self._job_path(job.id)
        payload = job.model_dump(mode="json")
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return job

    async def get(self, job_id: UUID) -> AnalysisJob:
        path = self._job_path(job_id)
        if not path.exists():
            raise KeyError(f"Unknown job id: {job_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return AnalysisJob.model_validate(payload)

    def _job_path(self, job_id: UUID) -> Path:
        return self._base_dir / f"{job_id}.json"
