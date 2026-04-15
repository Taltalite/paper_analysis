from __future__ import annotations

from pathlib import Path

from paper_analysis.adapters.parser.base import DocumentParser
from paper_analysis.domain.enums import AnalysisMode
from paper_analysis.domain.schemas import AnalysisExecution, AnalysisResult, ParsedDocument
from paper_analysis.runtime.crewai_runtime import CrewAIRuntime


class AnalysisService:
    def __init__(
        self,
        *,
        text_parser: DocumentParser,
        pdf_parser: DocumentParser,
        runtime: CrewAIRuntime,
    ) -> None:
        self._text_parser = text_parser
        self._pdf_parser = pdf_parser
        self._runtime = runtime

    async def parse_file(self, path: Path) -> ParsedDocument:
        parser = self._pdf_parser if path.suffix.lower() == ".pdf" else self._text_parser
        return await parser.parse(path)

    async def analyze_document(
        self,
        document: ParsedDocument,
        mode: AnalysisMode,
    ) -> AnalysisResult:
        return await self._runtime.run(mode, document)

    async def analyze_file(self, path: Path, mode: AnalysisMode) -> AnalysisExecution:
        parsed = await self.parse_file(path)
        result = await self.analyze_document(parsed, mode)
        return AnalysisExecution(document=parsed, result=result)
