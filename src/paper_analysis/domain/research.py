"""面向研究论文的四类结构化产物契约。

字段允许显式的 unknown / not_reported / not_applicable，避免把缺失信息
用常识或 0 值补齐。正式组装仍由运行时和 QC 负责。
"""
from __future__ import annotations

import math
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from paper_analysis.domain.execution import CoverageReport, SCHEMA_VERSION


class FindingKind(StrEnum):
    FACT = "fact"
    AUTHOR_CLAIM = "author_claim"
    OBSERVATION = "observation"
    INTERPRETATION = "interpretation"
    LIMITATION = "limitation"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"
    NOT_APPLICABLE = "not_applicable"
    NOT_REPORTED = "not_reported"


class EvidenceKind(StrEnum):
    TEXT = "text"
    CAPTION = "caption"
    VISION = "vision"
    TABLE = "table"
    PARSER = "parser"


class ResearchModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvidenceRef(ResearchModel):
    schema_version: str = SCHEMA_VERSION
    document_sha256: str = Field(min_length=1, max_length=128)
    evidence_id: str = Field(min_length=1, max_length=200)
    kind: EvidenceKind
    page: int | None = Field(default=None, ge=1)
    section: str | None = None
    block_id: str | None = Field(default=None, min_length=1, max_length=200)
    figure: str | None = Field(default=None, min_length=1, max_length=100)
    panel: str | None = Field(default=None, min_length=1, max_length=20)
    excerpt: str | None = Field(default=None, max_length=6000)
    observation: str | None = Field(default=None, max_length=6000)
    asset_sha256: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def has_locator(self) -> "EvidenceRef":
        if self.page is None and not self.block_id and not self.figure and not self.section:
            raise ValueError("EvidenceRef 至少需要 page、block_id 或 figure 定位。")
        if not self.excerpt and not self.observation:
            raise ValueError("EvidenceRef 需要原文摘录或图像观察。")
        return self


class DomainFinding(ResearchModel):
    schema_version: str = SCHEMA_VERSION
    finding_id: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=6000)
    claim_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    kind: FindingKind = FindingKind.FACT
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED

    @model_validator(mode="after")
    def unique_refs(self) -> "DomainFinding":
        if len(self.claim_ids) != len(set(self.claim_ids)):
            raise ValueError("DomainFinding 的 claim_ids 不能重复。")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("DomainFinding 的 evidence_ids 不能重复。")
        return self


StoryRole = Literal["problem", "hypothesis", "design", "result", "conclusion", "limitation"]


class StoryNode(ResearchModel):
    node_id: str = Field(min_length=1, max_length=200)
    role: StoryRole = "result"
    statement: str = Field(min_length=1, max_length=6000)
    claim_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED

class StoryEdge(ResearchModel):
    edge_id: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=200)
    target: str = Field(min_length=1, max_length=200)
    relation: str = Field(min_length=1, max_length=200)
    evidence_ids: list[str] = Field(default_factory=list)
    kind: FindingKind = FindingKind.INTERPRETATION


class StoryArchitecture(ResearchModel):
    schema_version: str = SCHEMA_VERSION
    nodes: list[StoryNode] = Field(default_factory=list)
    edges: list[StoryEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_graph(self) -> "StoryArchitecture":
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Story 节点 ID 不能重复。")
        edge_ids = [edge.edge_id for edge in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("Story 边 ID 不能重复。")
        known = set(node_ids)
        if any(edge.source not in known or edge.target not in known for edge in self.edges):
            raise ValueError("Story 边必须引用已存在的节点。")
        return self


class FlowNode(ResearchModel):
    node_id: str = Field(min_length=1, max_length=200)
    figure: str = Field(min_length=1, max_length=100)
    panel: str | None = Field(default=None, max_length=20)
    role: str = Field(min_length=1, max_length=200)
    claim_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    coverage_status: VerificationStatus = VerificationStatus.UNVERIFIED


class FlowEdge(ResearchModel):
    edge_id: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=200)
    target: str = Field(min_length=1, max_length=200)
    relation: str = Field(min_length=1, max_length=200)
    evidence_ids: list[str] = Field(default_factory=list)


class FigureFlow(ResearchModel):
    schema_version: str = SCHEMA_VERSION
    nodes: list[FlowNode] = Field(default_factory=list)
    edges: list[FlowEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_graph(self) -> "FigureFlow":
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Flow 节点 ID 不能重复。")
        edge_ids = [edge.edge_id for edge in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("Flow 边 ID 不能重复。")
        known = set(node_ids)
        if any(edge.source not in known or edge.target not in known for edge in self.edges):
            raise ValueError("Flow 边必须引用已存在的节点。")
        return self


class EvidenceMatrixRow(ResearchModel):
    finding_id: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=6000)
    sample_or_system: str = "not_reported"
    condition: str = "not_reported"
    assay: str = "not_reported"
    replicates: str = "not_reported"
    controls: str = "not_reported"
    effect_or_significance: str = "not_reported"
    limitations: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class MetricDirection(StrEnum):
    HIGHER_BETTER = "higher_better"
    LOWER_BETTER = "lower_better"
    NOT_COMPARABLE = "not_comparable"
    UNKNOWN = "unknown"


class BenchmarkEntry(ResearchModel):
    claim_ids: list[str] = Field(default_factory=list)
    entry_id: str = Field(min_length=1, max_length=200)
    method: str = Field(min_length=1, max_length=300)
    dataset: str = "not_reported"
    split: str = "not_reported"
    task: str = "not_reported"
    metric: str = Field(min_length=1, max_length=200)
    direction: MetricDirection = MetricDirection.UNKNOWN
    value_raw: str | None = Field(default=None, max_length=200)
    value: float | None = None
    unit: str | None = Field(default=None, max_length=100)
    uncertainty: str | None = Field(default=None, max_length=300)
    resource: str = "not_reported"
    evidence_ids: list[str] = Field(default_factory=list)
    value_source: Literal["explicit", "estimated_from_curve", "not_reported"] = "not_reported"

    @model_validator(mode="after")
    def validate_number(self) -> "BenchmarkEntry":
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("BenchmarkEntry.value 不能是 NaN 或 Inf。")
        if self.value is not None and not self.value_raw:
            raise ValueError("有数值时必须保留 value_raw 原始文本。")
        if self.value_source == "estimated_from_curve" and self.value is not None:
            # 曲线估读可以进入审计，但不会被确定性渲染器当作正式排名数值。
            if not self.uncertainty:
                self.uncertainty = "曲线估读；未提供正文/表格明示区间。"
        return self


class BenchmarkSection(ResearchModel):
    status: Literal["available", "not_applicable", "not_reported"] = "not_reported"
    reason: str = ""
    entries: list[BenchmarkEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_reason_for_empty(self) -> "BenchmarkSection":
        if self.status != "available" and not self.reason.strip():
            raise ValueError("无 benchmark 时必须说明 not_applicable 或 not_reported 的原因。")
        if self.status == "available" and not self.entries:
            raise ValueError("benchmark=available 时至少需要一条条目。")
        return self


class ResearchProducts(ResearchModel):
    schema_version: str = SCHEMA_VERSION
    findings: list[DomainFinding] = Field(default_factory=list)
    story: StoryArchitecture = Field(default_factory=StoryArchitecture)
    figure_flow: FigureFlow = Field(default_factory=FigureFlow)
    evidence_matrix: list[EvidenceMatrixRow] = Field(default_factory=list)
    benchmark: BenchmarkSection = Field(default_factory=lambda: BenchmarkSection(
        status="not_reported", reason="当前模型没有提供可定位的 benchmark 结构。"
    ))
    evidence: list[EvidenceRef] = Field(default_factory=list)
    coverage: CoverageReport = Field(default_factory=CoverageReport)

    @model_validator(mode="after")
    def validate_bindings(self) -> "ResearchProducts":
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("ResearchProducts 的 evidence_id 不能重复。")
        known_evidence = set(evidence_ids)
        finding_id_values = [item.finding_id for item in self.findings]
        if len(finding_id_values) != len(set(finding_id_values)):
            raise ValueError("ResearchProducts 的 finding_id 不能重复。")
        finding_ids = set(finding_id_values)
        known_claims = {
            claim_id for finding in self.findings for claim_id in finding.claim_ids
        }
        for finding in self.findings:
            if not set(finding.evidence_ids) <= known_evidence:
                raise ValueError("DomainFinding 引用了不存在的 evidence_id。")
        for row in self.evidence_matrix:
            if row.finding_id not in finding_ids:
                raise ValueError("EvidenceMatrixRow 必须绑定已存在的 finding_id。")
            if not set(row.evidence_ids) <= known_evidence:
                raise ValueError("EvidenceMatrixRow 引用了不存在的 evidence_id。")
        for node in self.story.nodes:
            if not set(node.claim_ids) <= known_claims:
                raise ValueError("StoryNode 引用了不存在的 claim_id。")
            if not set(node.evidence_ids) <= known_evidence:
                raise ValueError("StoryNode 引用了不存在的 evidence_id。")
        for edge in self.story.edges:
            if not edge.evidence_ids:
                raise ValueError("StoryEdge 必须绑定至少一个 evidence_id。")
            if not set(edge.evidence_ids) <= known_evidence:
                raise ValueError("StoryEdge 引用了不存在的 evidence_id。")
        flow_ids = {node.node_id for node in self.figure_flow.nodes}
        for node in self.figure_flow.nodes:
            if not set(node.claim_ids) <= known_claims:
                raise ValueError("FlowNode 引用了不存在的 claim_id。")
            if not set(node.evidence_ids) <= known_evidence:
                raise ValueError("FlowNode 引用了不存在的 evidence_id。")
        for edge in self.figure_flow.edges:
            if edge.source not in flow_ids or edge.target not in flow_ids:
                raise ValueError("FlowEdge 必须引用已存在的图组节点。")
            if not edge.evidence_ids or not set(edge.evidence_ids) <= known_evidence:
                raise ValueError("FlowEdge 必须绑定已存在的 evidence_id。")
        for entry in self.benchmark.entries:
            if not set(entry.evidence_ids) <= known_evidence:
                raise ValueError("BenchmarkEntry 引用了不存在的 evidence_id。")
        return self

