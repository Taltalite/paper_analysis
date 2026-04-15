from __future__ import annotations

from abc import ABC, abstractmethod

from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument


class AnalysisPipeline(ABC):
    @abstractmethod
    async def run(self, document: ParsedDocument) -> AnalysisResult:
        raise NotImplementedError
