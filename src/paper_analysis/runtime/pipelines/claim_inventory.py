from __future__ import annotations

import re

from paper_analysis.domain.models import ClaimEvidence, FigureAnalysis
from paper_analysis.domain.schemas import AnalysisResult


def collect_claims(
    *,
    analysis_result: AnalysisResult,
    figure_analyses: list[FigureAnalysis],
) -> list[ClaimEvidence]:
    collected: list[ClaimEvidence] = []
    raw_claims = analysis_result.structured_data.get("claims")
    if isinstance(raw_claims, list):
        for item in raw_claims:
            if not isinstance(item, dict):
                continue
            try:
                claim = ClaimEvidence.model_validate(item)
            except Exception:
                continue
            if claim.statement:
                collected.append(claim)

    if not collected:
        fallback_values = [analysis_result.summary, *analysis_result.key_points]
        extracted_notes = analysis_result.structured_data.get("extracted_notes")
        if isinstance(extracted_notes, dict):
            fallback_values.extend(
                str(extracted_notes.get(key, ""))
                for key in ("research_problem", "core_method", "main_results")
            )
        for index, value in enumerate(fallback_values, start=1):
            statement = _sanitize_text(value, max_length=400)
            if statement:
                collected.append(
                    ClaimEvidence(
                        claim_id=f"text-{index}",
                        statement=statement,
                        category="text_analysis",
                    )
                )

    start_index = len(collected) + 1
    for offset, analysis in enumerate(figure_analyses):
        statement = _sanitize_text(analysis.claimed_conclusion, max_length=400)
        if not statement or statement == "不足以判断":
            continue
        collected.append(
            ClaimEvidence(
                claim_id=f"figure-{start_index + offset}",
                statement=statement,
                category="figure_claim",
                source_sections=[analysis.figure_id] if analysis.figure_id else [],
                evidence=analysis.main_observations[:3],
                evidence_ids=[analysis.figure_id] if analysis.figure_id else [],
                confidence=analysis.confidence,
            )
        )
    return collected


def _sanitize_text(value: object, *, max_length: int) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_length].strip()
