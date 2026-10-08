"""将已有 parser、claim inventory 和 QC 结果组装为领域产品。

这里不新增模型调用，也不把自由文本自动升级为专家结论；所有 finding 都
保留 claim/evidence 引用和 verification_status。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from paper_analysis.domain.execution import CoverageReport, CoverageSet
from paper_analysis.domain.models import FigureAnalysis, FigureEvidence
from paper_analysis.domain.research import (
    BenchmarkEntry,
    BenchmarkSection,
    DomainFinding,
    EvidenceKind,
    EvidenceMatrixRow,
    EvidenceRef,
    FigureFlow,
    FindingKind,
    FlowEdge,
    FlowNode,
    MetricDirection,
    ResearchProducts,
    StoryArchitecture,
    StoryEdge,
    StoryNode,
    VerificationStatus,
)
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.pipelines.claim_inventory import collect_claims


def build_research_products(
    *,
    document: ParsedDocument,
    result: AnalysisResult,
    figure_evidence: list[FigureEvidence],
    figure_analyses: list[FigureAnalysis],
) -> ResearchProducts:
    registry = _evidence_registry(document, figure_evidence)
    claims = collect_claims(analysis_result=result, figure_analyses=figure_analyses)
    accepted = set(result.quality.accepted_claim_ids if result.quality else [])
    findings: list[DomainFinding] = []
    evidence_rows: list[EvidenceMatrixRow] = []
    for claim in claims:
        status = VerificationStatus.VERIFIED if claim.claim_id in accepted and claim.evidence_ids and set(claim.evidence_ids) <= set(registry) else VerificationStatus.UNVERIFIED
        kind = _finding_kind(claim.category, claim.claim_id)
        evidence_ids = [item for item in claim.evidence_ids if item in registry]
        finding = DomainFinding(
            finding_id=claim.claim_id,
            statement=claim.statement,
            claim_ids=[claim.claim_id],
            evidence_ids=evidence_ids,
            kind=kind,
            verification_status=status,
        )
        findings.append(finding)
        if status != VerificationStatus.VERIFIED:
            continue
        cited = " ".join((registry[eid].excerpt or "") for eid in evidence_ids)
        experiment = {key: value for key, value in claim.experiment.items()
                      if key in {"sample_or_system", "condition", "assay", "replicates", "controls", "effect_or_significance"}
                      and value and value in cited}
        evidence_rows.append(EvidenceMatrixRow(
            **experiment,
            finding_id=claim.claim_id,
            statement=claim.statement,
            evidence_ids=evidence_ids,
        ))

    story = _build_story(findings, claims, result)
    figure_flow = _build_figure_flow(document, figure_evidence, figure_analyses, findings, story)
    benchmark = _build_benchmark(result, evidence_ids=set(registry), claims=claims, accepted=accepted)
    evidence = list(registry.values())
    coverage = _build_coverage(document, result, figure_evidence, claims, accepted)
    return ResearchProducts(
        findings=findings,
        story=story,
        figure_flow=figure_flow,
        evidence_matrix=evidence_rows,
        benchmark=benchmark,
        evidence=evidence,
        coverage=coverage,
    )


def _evidence_registry(document: ParsedDocument, figures: list[FigureEvidence]) -> dict[str, EvidenceRef]:
    sha = str(document.metadata.get("document_sha256") or "unknown-document")
    registry: dict[str, EvidenceRef] = {}
    for block in document.metadata.get("ordered_blocks", []):
        if not isinstance(block, dict) or not block.get("block_id") or not block.get("text"):
            continue
        identifier = str(block["block_id"])
        page = _positive_int(block.get("page_number"))
        registry[identifier] = EvidenceRef(
            document_sha256=sha,
            evidence_id=identifier,
            kind=EvidenceKind.TEXT,
            page=page,
            block_id=identifier,
            excerpt=str(block["text"])[:6000],
        )
    for section, identifier in document.metadata.get("evidence_map", {}).get("sections", {}).items():
        original = document.metadata.get("qc_original_sections", document.sections)
        if original.get(section):
            registry[identifier] = EvidenceRef(document_sha256=sha, evidence_id=identifier,
                kind=EvidenceKind.TEXT, section=section, excerpt=original[section][:6000])
    evidence_by_id = {item.figure_id: item for item in figures}
    for figure in document.figures:
        parsed = evidence_by_id.get(figure.figure_id)
        observation = "\n".join(parsed.direct_evidence) if parsed else None
        kind = EvidenceKind.VISION if parsed and parsed.semantic_source == "multimodal_llm" else EvidenceKind.CAPTION
        asset_sha = _asset_hash(figure.page_snapshot_path)
        registry[figure.figure_id] = EvidenceRef(
            document_sha256=sha,
            evidence_id=figure.figure_id,
            kind=kind,
            page=figure.page_number,
            figure=figure.figure_id,
            excerpt=figure.caption[:6000] or "not_reported",
            observation=observation[:6000] if observation else None,
            asset_sha256=asset_sha,
        )
    return registry


def _build_story(findings: list[DomainFinding], claims: list, result: AnalysisResult) -> StoryArchitecture:
    by_id = {c.claim_id: c for c in claims}
    nodes = []
    for finding in findings:
        if finding.verification_status != VerificationStatus.VERIFIED:
            continue
        role = by_id[finding.finding_id].story_role
        if role not in {"problem", "hypothesis", "design", "result", "conclusion", "limitation"}:
            role = "result"
        nodes.append(StoryNode(node_id=finding.finding_id, role=role, statement=finding.statement,
            claim_ids=finding.claim_ids, evidence_ids=finding.evidence_ids, verification_status=finding.verification_status))
    known = {n.node_id for n in nodes}
    edges = []
    for i, edge in enumerate(result.structured_data.get("story_edges", [])):
        if not isinstance(edge, dict):
            continue
        claim = by_id.get(edge.get("claim_id"))
        if edge.get("source") in known and edge.get("target") in known and claim and claim.claim_id in known:
            edges.append(StoryEdge(edge_id=f"edge:{i}", source=edge["source"], target=edge["target"],
                relation=claim.statement[:200], evidence_ids=claim.evidence_ids))
    return StoryArchitecture(nodes=nodes, edges=edges)


def _build_figure_flow(
    document: ParsedDocument,
    figure_evidence: list[FigureEvidence],
    figure_analyses: list[FigureAnalysis],
    findings: list[DomainFinding],
    story: StoryArchitecture,
) -> FigureFlow:
    analysis_by_id = {item.figure_id: item for item in figure_analyses}
    evidence_by_id = {item.figure_id: item for item in figure_evidence}
    nodes: list[FlowNode] = []
    for figure in document.figures:
        evidence = evidence_by_id.get(figure.figure_id)
        analysis = analysis_by_id.get(figure.figure_id)
        if evidence is None and analysis is None:
            continue
        bound = [finding for finding in findings if finding.verification_status == VerificationStatus.VERIFIED
                 and figure.figure_id in finding.evidence_ids]
        status = VerificationStatus.VERIFIED if bound else VerificationStatus.UNVERIFIED
        nodes.append(FlowNode(
            node_id=f"flow:{figure.figure_id}",
            figure=figure.figure_id,
            role=("；".join(f.statement for f in bound) or "尚无通过核验的图表结论")[:200],
            claim_ids=[f.finding_id for f in bound],
            evidence_ids=[figure.figure_id],
            coverage_status=status,
        ))
    edges = []
    for edge in story.edges:
        for source in nodes:
            for target in nodes:
                if source != target and edge.source in source.claim_ids and edge.target in target.claim_ids:
                    edges.append(FlowEdge(edge_id=f"flow:{len(edges)}", source=source.node_id,
                        target=target.node_id, relation=edge.relation, evidence_ids=edge.evidence_ids))
    return FigureFlow(nodes=nodes, edges=edges)


def _build_benchmark(result: AnalysisResult, *, evidence_ids: set[str], claims: list, accepted: set[str]) -> BenchmarkSection:
    raw = result.structured_data.get("benchmark")
    reason = result.structured_data.get("benchmark_not_applicable_reason")
    if isinstance(raw, dict):
        status = raw.get("status", "not_reported")
        entries = raw.get("entries", [])
        parsed_entries: list[BenchmarkEntry] = []
        if isinstance(entries, list):
            for index, value in enumerate(entries):
                if not isinstance(value, dict):
                    continue
                try:
                    refs = value.get("evidence_ids", [])
                    cids = value.get("claim_ids", [])
                    bound = [c for c in claims if c.claim_id in cids and c.claim_id in accepted]
                    if not refs or not set(refs) <= evidence_ids or not cids or len(bound) != len(set(cids)):
                        continue
                    if not set(refs) <= {eid for c in bound for eid in c.evidence_ids}:
                        continue
                    source = " ".join(c.statement + " " + " ".join(c.evidence) for c in bound)
                    if value.get("value_source") != "explicit" or not value.get("value_raw"):
                        continue
                    if any(not value.get(k) or str(value[k]) not in source for k in ("method", "metric", "value_raw")):
                        continue
                    value = dict(value)
                    for key in ("dataset", "split", "task", "resource", "unit", "uncertainty"):
                        if value.get(key) and str(value[key]) not in source:
                            value[key] = None if key in {"unit", "uncertainty"} else "not_reported"
                    # 展示原始数值，禁止未经确定性解析的归一化数值改变原意。
                    try:
                        value["value"] = float(value["value_raw"])
                    except (ValueError, TypeError):
                        value["value"] = None
                    parsed_entries.append(BenchmarkEntry.model_validate({
                        "claim_ids": cids,
                        "entry_id": value.get("entry_id") or f"benchmark:{index + 1}",
                        "method": value.get("method") or "not_reported",
                        "dataset": value.get("dataset", "not_reported"),
                        "split": value.get("split", "not_reported"),
                        "task": value.get("task", "not_reported"),
                        "metric": value.get("metric") or "not_reported",
                        "direction": value.get("direction", MetricDirection.UNKNOWN),
                        "value_raw": value.get("value_raw"),
                        "value": value.get("value"),
                        "unit": value.get("unit"),
                        "uncertainty": value.get("uncertainty"),
                        "resource": value.get("resource", "not_reported"),
                        "evidence_ids": [
                            str(item) for item in value.get("evidence_ids", [])
                            if str(item) in evidence_ids
                        ],
                        "value_source": value.get("value_source", "not_reported"),
                    }))
                except Exception:
                    continue
        if status == "available" and parsed_entries:
            return BenchmarkSection(status="available", entries=parsed_entries, reason=str(raw.get("reason", "")))
        if status == "not_applicable":
            return BenchmarkSection(status="not_applicable", reason=str(raw.get("reason") or reason or "论文未包含适用的 benchmark。"))
    if reason:
        return BenchmarkSection(status="not_applicable", reason=str(reason))
    return BenchmarkSection(status="not_reported", reason="尚未提取可定位的 benchmark 结构；不能据此生成排行榜。")


def _build_coverage(document, result, figure_evidence, claims, accepted) -> CoverageReport:  # noqa: ANN001
    candidates = CoverageSet(
        sections=list(document.section_order),
        figures=[figure.figure_id for figure in document.figures],
        claims=[claim.claim_id for claim in claims],
    )
    selected_sections = result.structured_data.get("selected_sections", document.section_order)
    selected = CoverageSet(
        sections=[str(item) for item in selected_sections if str(item) in document.section_order],
        figures=[item.figure_id for item in figure_evidence],
        claims=[claim.claim_id for claim in claims],
    )
    verified_ids = {eid for claim in claims if claim.claim_id in accepted for eid in claim.evidence_ids}
    verified_figures = [item.figure_id for item in figure_evidence
                        if item.figure_id in verified_ids and item.figure_id in result.structured_data.get("visually_reviewed_figures", [])]
    return CoverageReport(
        candidate=candidates,
        selected=selected,
        read=selected,
        verified=CoverageSet(
            sections=[name for name, eid in document.metadata.get("evidence_map", {}).get("sections", {}).items() if eid in verified_ids],
            figures=verified_figures,
            claims=[claim_id for claim_id in candidates.claims if claim_id in accepted],
        ),
        skipped={
            "sections": [item for item in candidates.sections if item not in selected.sections],
            "figures": [item for item in candidates.figures if item not in selected.figures],
            "claims": [item for item in candidates.claims if item not in accepted],
        },
    )


def _finding_kind(category: str, claim_id: str) -> FindingKind:
    text = f"{category} {claim_id}".lower()
    if "figure" in text or "visual" in text:
        return FindingKind.OBSERVATION
    if "author" in text or "claim" in text:
        return FindingKind.AUTHOR_CLAIM
    if "limit" in text:
        return FindingKind.LIMITATION
    return FindingKind.FACT


def _asset_hash(path: str | None) -> str | None:
    if not path:
        return None
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _positive_int(value: Any) -> int | None:
    try:
        integer = int(value)
    except (TypeError, ValueError):
        return None
    return integer if integer > 0 else None

