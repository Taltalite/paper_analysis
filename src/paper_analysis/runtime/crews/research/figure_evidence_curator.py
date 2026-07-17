from __future__ import annotations

import re
from typing import Protocol

from paper_analysis.domain.models import (
    FigureEvidence,
    FigureEvidenceBatch,
    FigureMetadata,
    FigureSemanticArtifact,
    FigureSemanticArtifactBatch,
)
from paper_analysis.domain.schemas import ParsedDocument


class FigureEvidenceCuratorRunner(Protocol):
    def run(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
        semantic_artifacts: FigureSemanticArtifactBatch,
    ) -> FigureEvidenceBatch:
        ...


class DeterministicFigureEvidenceCurator:
    """Merges parser and semantic evidence without an extra agent round-trip."""

    def run(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
        semantic_artifacts: FigureSemanticArtifactBatch,
    ) -> FigureEvidenceBatch:
        del document
        artifact_map = {artifact.figure_id: artifact for artifact in semantic_artifacts.artifacts}
        evidences = [
            _fallback_evidence(figure=figure, artifact=artifact_map.get(figure.figure_id))
            for figure in figures
        ]
        return FigureEvidenceBatch(evidences=evidences)


def _fallback_evidence(
    *,
    figure: FigureMetadata,
    artifact: FigureSemanticArtifact | None,
) -> FigureEvidence:
    figure_type = artifact.figure_type if artifact and artifact.figure_type else "unknown"
    metrics = artifact.axes if artifact else []
    direct_evidence = list(artifact.direct_evidence if artifact else [])
    if figure.caption:
        direct_evidence.insert(0, f"caption 摘要：{_sanitize_text(figure.caption, max_length=120)}")
    return FigureEvidence(
        figure_id=_sanitize_text(figure.figure_id, max_length=40),
        figure_title_or_caption=_sanitize_text(figure.caption, max_length=120),
        page_number=figure.page_number,
        figure_type=figure_type,
        compared_items=_infer_compared_items(figure),
        metrics_or_axes=_sanitize_list(metrics, max_items=6, max_length=80),
        direct_evidence=_sanitize_list(direct_evidence, max_items=6, max_length=200),
        referenced_text_spans=_sanitize_list(figure.referenced_text_spans, max_items=4, max_length=220),
        semantic_source=artifact.extraction_source if artifact else "unknown",
        evidence_quality=(artifact.confidence if artifact else "低") or "不足以判断",
        uncertainties=_sanitize_list(artifact.uncertainties if artifact else [], max_items=6, max_length=160),
    )


def _infer_compared_items(figure: FigureMetadata) -> list[str]:
    text = " ".join([figure.caption, *figure.referenced_text_spans])
    parts = re.split(r"\b(vs\.?|versus|compared with|against)\b", text, flags=re.IGNORECASE)
    if len(parts) >= 3:
        return [_sanitize_text(parts[0], max_length=60), _sanitize_text(parts[-1], max_length=60)]
    return []


def _sanitize_text(value: object, *, max_length: int = 320) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_length].strip()


def _sanitize_list(
    value: object,
    *,
    max_items: int = 4,
    max_length: int = 120,
) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    sanitized: list[str] = []
    for item in value:
        text = _sanitize_text(item, max_length=max_length)
        if text:
            sanitized.append(text)
        if len(sanitized) >= max_items:
            break
    return sanitized
