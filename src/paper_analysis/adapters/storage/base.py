from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

from paper_analysis.domain.schemas import AnalysisJob


class ArtifactStorage(ABC):
    @abstractmethod
    async def write_text(self, path: Path, content: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def write_json(self, path: Path, payload: dict) -> str:
        raise NotImplementedError

    @abstractmethod
    async def read_text(self, path: Path) -> str:
        raise NotImplementedError

    @abstractmethod
    async def read_json(self, path: Path) -> dict:
        raise NotImplementedError


class JobStore(ABC):
    @abstractmethod
    async def save(self, job: AnalysisJob) -> AnalysisJob:
        raise NotImplementedError

    @abstractmethod
    async def get(self, job_id: UUID) -> AnalysisJob:
        raise NotImplementedError
