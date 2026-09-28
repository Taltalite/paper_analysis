from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel

from paper_analysis.domain.qa import QuestionJob


def atomic_json(path: Path, value: BaseModel | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    data = value.model_dump_json(indent=2) if isinstance(value, BaseModel) else json.dumps(value, ensure_ascii=False, indent=2)
    temporary.write_text(data, encoding="utf-8")
    temporary.replace(path)


class QuestionStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def directory(self, identifier: UUID) -> Path:
        return self.root / str(identifier)

    def save(self, job: QuestionJob) -> None:
        job.updated_at = datetime.now(UTC)
        atomic_json(self.directory(job.id) / "job.json", job)

    def get(self, identifier: UUID) -> QuestionJob:
        return QuestionJob.model_validate_json((self.directory(identifier) / "job.json").read_text())

    def list(self) -> list[QuestionJob]:
        jobs = []
        for path in self.root.glob("*/job.json"):
            jobs.append(QuestionJob.model_validate_json(path.read_text()))
        return sorted(jobs, key=lambda job: job.created_at, reverse=True)
