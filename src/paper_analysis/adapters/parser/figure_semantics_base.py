from __future__ import annotations

from typing import Protocol

from paper_analysis.domain.models import FigureMetadata, FigureSemanticArtifactBatch
from paper_analysis.domain.schemas import ParsedDocument


class FigureSemanticExtractor(Protocol):
    def extract(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
    ) -> FigureSemanticArtifactBatch:
        ...
