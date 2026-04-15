from __future__ import annotations

from pathlib import Path

from paper_analysis.adapters.storage.base import ArtifactStorage
from paper_analysis.domain.schemas import AnalysisArtifact, AnalysisResult, ParsedDocument


class ArtifactService:
    def __init__(self, *, storage: ArtifactStorage) -> None:
        self._storage = storage

    async def save_markdown_report(self, path: Path, content: str) -> str:
        return await self._storage.write_text(path, content)

    async def save_json_report(self, path: Path, payload: dict) -> str:
        return await self._storage.write_json(path, payload)

    async def read_markdown_report(self, path: Path) -> str:
        return await self._storage.read_text(path)

    async def read_json_report(self, path: Path) -> dict:
        return await self._storage.read_json(path)

    async def save_analysis_result(
        self,
        *,
        markdown_path: Path,
        json_path: Path,
        result: AnalysisResult,
        document: ParsedDocument | None = None,
    ) -> AnalysisArtifact:
        markdown_report_path = await self.save_markdown_report(markdown_path, result.markdown_report)
        json_report_path = await self.save_json_report(json_path, result.model_dump())
        parsed_markdown_path: str | None = None
        if document is not None and document.metadata.get("parser_kind") == "pdf" and document.markdown:
            parsed_path = markdown_path.with_name(f"{markdown_path.stem}.parsed.md")
            parsed_markdown_path = await self.save_markdown_report(parsed_path, document.markdown)
        return AnalysisArtifact(
            markdown_report_path=markdown_report_path,
            json_report_path=json_report_path,
            parsed_markdown_path=parsed_markdown_path,
        )
