"""零模型调用的交付闸门；模糊对应宁可待复核，不使用相似度猜测放行。"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict

from paper_analysis.domain.models import FactCheckBatch, FigureAnalysis, FigureEvidence
from paper_analysis.domain.quality import QualityIssue, QualityReport, ReportBinding
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.pipelines.claim_inventory import collect_claims

PENDING = "待核验：尚未建立与获支持主张的一致对应关系。"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).strip('"\'“”')


def _evidence_registry(document: ParsedDocument, figures: list[FigureEvidence]) -> dict[str, str]:
    registry: dict[str, str] = {}
    mapping = document.metadata.get("evidence_map", {}).get("sections", {})
    original_sections = document.metadata.get("qc_original_sections", document.sections)
    for section, identifier in mapping.items():
        if section in original_sections:
            registry[str(identifier)] = original_sections[section]
    for block in document.metadata.get("ordered_blocks", []):
        if isinstance(block, dict) and block.get("block_id") and block.get("text"):
            registry[str(block["block_id"])] = str(block["text"])
    # 图号只能来自当前 parser；视觉抽取内容是模型证据，不冒充独立金标准。
    evidence_by_id = {item.figure_id: item for item in figures}
    for figure in document.figures:
        chunks = [figure.caption, *figure.referenced_text_spans]
        evidence = evidence_by_id.get(figure.figure_id)
        if evidence and evidence.semantic_source == "multimodal_llm":
            chunks.extend([*evidence.direct_evidence, *evidence.visible_text])
        registry[figure.figure_id] = "\n".join(chunks)
    return registry


def apply_quality_gate(
    *, document: ParsedDocument, result: AnalysisResult,
    figure_analyses: list[FigureAnalysis], figure_evidence: list[FigureEvidence],
    fact_checks: FactCheckBatch,
) -> list[FigureAnalysis]:
    """同步 JSON 的交付字段与 QC 状态，返回供 Markdown 使用的受限图表结论。

    qc_draft 保留首次处理的原始生成结果；重复渲染会重新评估该快照，避免层层套娃。
    """
    previous = result.structured_data.get("qc_draft")
    draft = AnalysisResult.model_validate(previous) if isinstance(previous, dict) else result.model_copy(deep=True)
    snapshot = draft.model_dump(exclude={"quality", "markdown_report"})
    original_figures = draft.structured_data.get("figure_analyses")
    if isinstance(original_figures, list):
        figure_analyses = [FigureAnalysis.model_validate(item) for item in original_figures]
    claims = collect_claims(analysis_result=draft, figure_analyses=figure_analyses)
    registry = _evidence_registry(document, figure_evidence)
    qc = QualityReport(
        expected_claims=len(claims),
        evidence_ids=sorted(registry),
        document_fingerprint=hashlib.sha256(json.dumps(registry, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
    )
    expected_fingerprint = result.structured_data.get("qc_original_evidence_fingerprint")
    if not expected_fingerprint and result.quality is not None:
        expected_fingerprint = result.quality.document_fingerprint
    source_changed = bool(expected_fingerprint and expected_fingerprint != qc.document_fingerprint)
    if source_changed:
        qc.issues.append(QualityIssue(
            code="source_changed", severity="critical", location="document",
            message="证据索引内容与上次 QC 不一致，不能复用旧核验判定。",
            action="使用对应原文版本，或重新核验受影响主张。",
        ))

    def issue(code: str, location: str, message: str, claim_id: str = "") -> None:
        qc.issues.append(QualityIssue(code=code, location=location, message=message, claim_id=claim_id))

    counts = Counter(claim.claim_id for claim in claims)
    checks_by_id = defaultdict(list)
    for check in fact_checks.checks:
        checks_by_id[check.claim_id].append(check)
        if check.claim_id not in counts:
            issue("unknown_check", "fact_checks", "核验结果引用了不存在的主张。", check.claim_id)
    if not claims:
        issue("no_claims", "claims", "没有可核验的主张，不能默认通过。")
    raw_claims = draft.structured_data.get("claims")
    if isinstance(raw_claims, list):
        from pydantic import ValidationError
        from paper_analysis.domain.models import ClaimEvidence
        for index, raw in enumerate(raw_claims):
            try:
                parsed = ClaimEvidence.model_validate(raw)
                if not parsed.statement.strip():
                    raise ValueError("empty statement")
            except (ValidationError, ValueError):
                qc.invalid_claims += 1
                issue("invalid_claim", f"claims[{index}]", "主张结构无效或陈述为空，未纳入有效核验。")

    accepted: dict[str, list[str]] = defaultdict(list)
    accepted_statements: list[str] = []
    for claim in claims:
        identifier = claim.claim_id
        location = f"claims.{identifier}"
        if not identifier or counts[identifier] != 1:
            issue("invalid_claim_id", location, "主张 ID 为空或重复，无法唯一对应。", identifier)
            continue
        matches = checks_by_id[identifier]
        if len(matches) != 1:
            code = "missing_check" if not matches else "duplicate_check"
            issue(code, location, "缺少核验结果或存在多条核验结果；不得默认放行。", identifier)
            continue
        check = matches[0]
        if _normalize(check.claim) != _normalize(claim.statement):
            issue("claim_mismatch", location, "核验文本与原主张不一致，不能仅凭相同 ID 放行。", identifier)
            continue
        if source_changed:
            continue
        qc.checked_claims += 1
        refs = list(dict.fromkeys([*claim.evidence_ids, *check.evidence_ids]))
        invalid = [ref for ref in refs if ref not in registry]
        if invalid:
            issue("invalid_evidence", location, f"证据 ID 不存在于当前文档：{'、'.join(invalid)}。", identifier)
        if check.verdict != "supported":
            issue("not_supported", location, f"核验判定为 {check.verdict}，保留为待复核内容。", identifier)
            continue
        if invalid:
            continue
        if not check.evidence_ids:
            issue("missing_evidence", location, "支持判定没有提供可定位的证据 ID。", identifier)
            continue
        cited = [_normalize(registry[ref]) for ref in check.evidence_ids]
        # 兼容“章节名：\"原文\"”式引用，只提取完整引号中的文字，不作语义猜测。
        snippets: list[str] = []
        for text in [*claim.evidence, *check.evidence_refs]:
            snippets.append(_normalize(text))
            snippets.extend(_normalize(quote) for quote in re.findall(r'["“]([^"”]{12,})["”]', text))
        if not any(len(snippet) >= 12 and any(snippet in source for source in cited) for snippet in snippets):
            issue("unlocated_evidence", location, "无法在引用位置找到证据片段；仅有 ID 不足以通过定位检查。", identifier)
            continue
        accepted[_normalize(claim.statement)].append(identifier)
        accepted_statements.append(claim.statement)
        qc.accepted_claim_ids.append(identifier)

    def release(value: str, location: str) -> str:
        if not value.strip():
            return value
        identifiers = accepted.get(_normalize(value), [])
        qc.bindings.append(ReportBinding(location=location, claim_ids=identifiers, released=bool(identifiers)))
        if not identifiers:
            issue("unbound_report_field", location, "报告文本未与可交付主张精确对应，已移入原始草稿。")
            return PENDING
        return value

    # 正式摘要由可交付主张原句组合，避免对一段自由生成摘要作整体背书。
    release(draft.summary, "draft.summary")
    result.summary = "\n".join(dict.fromkeys(accepted_statements)) or "暂无满足交付条件的主张，请查看 QC 问题清单。"
    qc.bindings.append(ReportBinding(location="summary", claim_ids=qc.accepted_claim_ids, released=bool(qc.accepted_claim_ids)))
    qc.bindings.append(ReportBinding(location="conclusion", claim_ids=qc.accepted_claim_ids, released=bool(qc.accepted_claim_ids)))
    result.key_points = [release(text, f"key_points[{i}]") for i, text in enumerate(draft.key_points)]
    result.limitations = [release(text, f"limitations[{i}]") for i, text in enumerate(draft.limitations)]
    structured = draft.model_copy(deep=True).structured_data
    notes = structured.get("extracted_notes")
    if isinstance(notes, dict):
        for key, value in notes.items():
            if isinstance(value, str):
                notes[key] = release(value, f"extracted_notes.{key}")
            elif isinstance(value, list):
                notes[key] = [release(str(text), f"extracted_notes.{key}[{i}]") for i, text in enumerate(value)]
    for key in ("novelty", "reproducibility", "strengths", "limitations"):
        value = structured.get(key)
        if isinstance(value, str):
            structured[key] = release(value, key)
        elif isinstance(value, list):
            structured[key] = [release(str(text), f"{key}[{i}]") for i, text in enumerate(value)]
    gated_figures: list[FigureAnalysis] = []
    for figure in figure_analyses:
        gated = figure.model_copy(deep=True)
        gated.compared_items = [release(text, f"figures.{figure.figure_id}.compared_items[{i}]") for i, text in enumerate(figure.compared_items)]
        gated.claimed_conclusion = release(figure.claimed_conclusion, f"figures.{figure.figure_id}.conclusion")
        gated.main_observations = [release(text, f"figures.{figure.figure_id}.observations[{i}]") for i, text in enumerate(figure.main_observations)]
        gated.consistency_check = release(figure.consistency_check, f"figures.{figure.figure_id}.consistency")
        if gated.claimed_conclusion == PENDING or gated.consistency_check == PENDING:
            gated.confidence = "待人工复核"
        gated_figures.append(gated)
    structured["figure_analyses"] = [figure.model_dump() for figure in gated_figures]
    structured["qc_draft"] = snapshot
    structured["qc_original_evidence_fingerprint"] = expected_fingerprint or qc.document_fingerprint
    result.structured_data = structured
    qc.status = "blocked" if not qc.accepted_claim_ids else ("needs_review" if qc.issues else "passed")
    result.quality = qc
    return gated_figures
