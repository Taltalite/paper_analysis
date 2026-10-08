from __future__ import annotations

from typing import Protocol

from paper_analysis.adapters.parser.figure_semantics_base import FigureSemanticExtractor
from paper_analysis.domain.models import FigureMetadata, FigureSemanticArtifactBatch
from paper_analysis.domain.schemas import ParsedDocument
from paper_analysis.runtime.budget import BudgetLedger


class FigureGroundingRunner(Protocol):
    def run(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
        execution_context: BudgetLedger | None = None,
    ) -> FigureSemanticArtifactBatch:
        ...


class AdapterFigureGroundingRunner:
    """Runs the semantic extractor without spending an additional LLM call."""

    def __init__(self, *, extractor: FigureSemanticExtractor) -> None:
        self._extractor = extractor

    def run(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
        execution_context: BudgetLedger | None = None,
    ) -> FigureSemanticArtifactBatch:
        if execution_context is None:
            return self._extractor.extract(document=document, figures=figures)
        try:
            return self._extractor.extract(
                document=document, figures=figures, execution_context=execution_context
            )
        except TypeError:
            return self._extractor.extract(document=document, figures=figures)
