from __future__ import annotations

from abc import ABC, abstractmethod

from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.budget import BudgetLedger
from paper_analysis.domain.execution import ResolvedPolicy


class AnalysisPipeline(ABC):
    @abstractmethod
    async def run(
        self,
        document: ParsedDocument,
        policy: ResolvedPolicy | None = None,
        execution_context: BudgetLedger | None = None,
    ) -> AnalysisResult:
        raise NotImplementedError
