from __future__ import annotations

import re

from paper_analysis.domain.models import ClaimEvidence, FigureEvidence
from paper_analysis.domain.schemas import ParsedDocument

_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*%?")
_MAX_FLAGS = 30
_MAX_PROBES_PER_CLAIM = 3


def run_fact_check_prechecks(
    *,
    document: ParsedDocument,
    claims: list[ClaimEvidence],
    figure_evidence: list[FigureEvidence],
) -> list[str]:
    """确定性规则预检查（零 LLM）。

    输出给事实检查 agent 的提示性 flags：
    - 未引用 evidence ID / 来源章节的核心主张
    - 证据片段无法回指原文的主张
    - 主张中的数值在原文与图表证据中均不存在
    """
    flags: list[str] = []
    haystack = _build_haystack(document=document, figure_evidence=figure_evidence)
    for claim in claims:
        label = claim.claim_id or "未编号主张"
        if not claim.evidence_ids and not claim.source_sections:
            flags.append(f"{label}：未引用 evidence ID 或来源章节，核验时需额外谨慎。")
        for snippet in claim.evidence[:_MAX_PROBES_PER_CLAIM]:
            probe = snippet.strip()[:40]
            if probe and probe not in document.raw_text:
                flags.append(f"{label}：证据片段未在原文中找到（可能被改写或虚构）：{probe}")
        for number in _numbers_of(claim.statement):
            if not _number_present(number, haystack):
                flags.append(f"{label}：数值 {number} 未在原文或图表证据中出现。")
        if len(flags) >= _MAX_FLAGS:
            break
    return flags[:_MAX_FLAGS]


def _build_haystack(
    *,
    document: ParsedDocument,
    figure_evidence: list[FigureEvidence],
) -> str:
    chunks = [document.raw_text]
    for evidence in figure_evidence:
        chunks.extend(evidence.direct_evidence)
        chunks.extend(evidence.referenced_text_spans)
        chunks.extend(evidence.metrics_or_axes)
    return "\n".join(chunks)


def _numbers_of(text: str) -> list[str]:
    numbers: list[str] = []
    for match in _NUMBER_PATTERN.finditer(text):
        token = match.group(0).strip()
        if token and token not in numbers:
            numbers.append(token)
    return numbers


def _number_present(token: str, haystack: str) -> bool:
    if token in haystack:
        return True
    compact_token = token.replace(" ", "")
    compact_haystack = haystack.replace(" ", "")
    if compact_token in compact_haystack:
        return True
    digits = compact_token.rstrip("%")
    return bool(digits) and digits in compact_haystack
