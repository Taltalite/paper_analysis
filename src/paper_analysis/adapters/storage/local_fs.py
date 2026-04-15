from __future__ import annotations

import json
from pathlib import Path

from paper_analysis.adapters.storage.base import ArtifactStorage


class LocalFilesystemArtifactStorage(ArtifactStorage):
    async def write_text(self, path: Path, content: str) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path)

    async def write_json(self, path: Path, payload: dict) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

    async def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    async def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))
