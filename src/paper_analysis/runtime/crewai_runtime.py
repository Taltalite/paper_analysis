from __future__ import annotations

from paper_analysis.domain.enums import AnalysisMode
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.pipelines.general_text import GeneralTextPipeline
from paper_analysis.runtime.pipelines.research_paper import ResearchPaperPipeline


class CrewAIRuntime:
    def __init__(
        self,
        *,
        general_text_pipeline: GeneralTextPipeline,
        research_paper_pipeline: ResearchPaperPipeline,
    ) -> None:
        self._general_text_pipeline = general_text_pipeline
        self._research_paper_pipeline = research_paper_pipeline

    async def run(self, mode: AnalysisMode, document: ParsedDocument) -> AnalysisResult:
        if mode == AnalysisMode.GENERAL_TEXT:
            return await self._general_text_pipeline.run(document)
        if mode == AnalysisMode.RESEARCH_PAPER:
            return await self._research_paper_pipeline.run(document)
        raise ValueError(f"Unsupported mode: {mode}")
