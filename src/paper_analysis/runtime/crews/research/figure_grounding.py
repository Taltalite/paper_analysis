from __future__ import annotations

from typing import Protocol

from paper_analysis.adapters.parser.figure_semantics_base import FigureSemanticExtractor
from paper_analysis.domain.models import FigureMetadata, FigureSemanticArtifactBatch
from paper_analysis.domain.schemas import ParsedDocument


class FigureGroundingRunner(Protocol):
    def run(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
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
    ) -> FigureSemanticArtifactBatch:
        return self._extractor.extract(document=document, figures=figures)
