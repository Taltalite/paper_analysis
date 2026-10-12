"""版本化参考集与独立评价协议；AI 暂定参考不冒充专家金标准。"""
from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReferencePaper(EvaluationModel):
    source_path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    title: str
    doi: str
    page_count: int = Field(ge=1)


class ReferenceEvidence(EvaluationModel):
    evidence_id: str
    source_kind: Literal["text", "caption", "vision"]
    pdf_page_1_based: int = Field(ge=1)
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)
    figure: str | None = None
    panel: str | None = None
    verbatim_quote: str | None = None
    visual_observation: str | None = None
    legibility: Literal["clear", "ambiguous", "unreadable", "not_applicable"] = "clear"

    @model_validator(mode="after")
    def source_contract(self) -> "ReferenceEvidence":
        if self.source_kind == "vision":
            if not self.visual_observation or self.verbatim_quote or not self.figure:
                raise ValueError("视觉证据必须记录图号与直接观察，不得用引文替代。")
        elif not self.verbatim_quote or self.visual_observation:
            raise ValueError("正文/图注证据必须有原文定位片段。")
        if self.bbox and (not all(isfinite(x) for x in self.bbox) or not (self.bbox[0] < self.bbox[2] and self.bbox[1] < self.bbox[3])):
            raise ValueError("证据 bbox 必须有正面积。")
        return self


class ReferenceClaim(EvaluationModel):
    claim_id: str
    statement: str = Field(min_length=1)
    basis: Literal["text", "visual"]
    evidence_ids: list[str] = Field(min_length=1)
    required: bool = True


class ReferenceCase(EvaluationModel):
    candidate_id: str
    paper_id: str
    question: str = Field(min_length=1, max_length=2000)
    task_kind: Literal["text", "numeric", "visual", "absence"]
    figure: str | None = None
    panel: str | None = None
    expected_status: Literal["answered", "partial", "refused"]
    reference_answer: str
    gold_claims: list[ReferenceClaim] = Field(default_factory=list)
    gold_evidence: list[ReferenceEvidence] = Field(default_factory=list)
    required_uncertainties: list[str] = Field(default_factory=list)
    forbidden_inferences: list[str] = Field(default_factory=list)
    absence_check: str | None = None

    @model_validator(mode="after")
    def links(self) -> "ReferenceCase":
        evidence = {item.evidence_id: item for item in self.gold_evidence}
        if len(evidence) != len(self.gold_evidence) or len({c.claim_id for c in self.gold_claims}) != len(self.gold_claims):
            raise ValueError("参考主张/证据 ID 必须唯一。")
        for claim in self.gold_claims:
            if not set(claim.evidence_ids) <= evidence.keys():
                raise ValueError("参考主张引用未知证据。")
            if claim.basis == "visual" and not any(evidence[i].source_kind == "vision" for i in claim.evidence_ids):
                raise ValueError("视觉主张必须绑定视觉证据。")
        if self.panel and not self.figure:
            raise ValueError("子图必须同时绑定图号。")
        if self.expected_status != "refused" and not self.gold_claims:
            raise ValueError("可回答题必须有参考主张。")
        if self.task_kind == "absence" and (not self.absence_check or self.gold_claims):
            raise ValueError("不存在的图应记录全文检查范围，不编造主张或页码。")
        return self


class ReferenceDataset(EvaluationModel):
    schema_version: Literal["reference-qa-v1"] = "reference-qa-v1"
    dataset_id: str
    reference_status: Literal["ai_provisional", "expert_adjudicated"] = "ai_provisional"
    created_at: datetime
    provenance: str
    papers: dict[str, ReferencePaper]
    cases: list[ReferenceCase] = Field(min_length=1)

    @model_validator(mode="after")
    def case_contract(self) -> "ReferenceDataset":
        if len({c.candidate_id for c in self.cases}) != len(self.cases):
            raise ValueError("问题 ID 必须唯一。")
        for case in self.cases:
            if case.paper_id not in self.papers:
                raise ValueError("问题引用未知论文。")
            if any(e.pdf_page_1_based > self.papers[case.paper_id].page_count for e in case.gold_evidence):
                raise ValueError("证据页码越界。")
        return self


ErrorCategory = Literal["execution", "parser", "retrieval", "vision", "answer", "verification", "citation", "status", "unknown"]


class ClaimReview(EvaluationModel):
    answer_claim_id: str
    matched_gold_claim_ids: list[str] = Field(default_factory=list)
    correctness: Literal["correct", "incorrect", "unverifiable"]
    citation_correct: bool | None = None
    panel_aligned: bool | None = None
    reason: str = Field(min_length=1)


class CaseReview(EvaluationModel):
    candidate_id: str
    answer_id: str | None = None
    answer_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    claim_reviews: list[ClaimReview] = Field(default_factory=list)
    # 缺省表示尚未评价，而不是通过。
    uncertainty_correct: bool | None = None
    forbidden_inference_present: bool | None = None
    primary_error: ErrorCategory | None = None
    secondary_errors: list[ErrorCategory] = Field(default_factory=list)
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def answer_binding(self) -> "CaseReview":
        if bool(self.answer_id) != bool(self.answer_sha256):
            raise ValueError("评价必须同时绑定回答 ID 与文件指纹。")
        if len({c.answer_claim_id for c in self.claim_reviews}) != len(self.claim_reviews):
            raise ValueError("回答主张不得重复评价。")
        return self


class ReviewBundle(EvaluationModel):
    schema_version: Literal["qa-review-v1"] = "qa-review-v1"
    dataset_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    run_id: str
    reviewer: str
    review_kind: Literal["ai_assisted", "human"]
    cases: list[CaseReview]

    @model_validator(mode="after")
    def unique_cases(self) -> "ReviewBundle":
        if len({c.candidate_id for c in self.cases}) != len(self.cases):
            raise ValueError("题目不得重复评价。")
        return self


class ScoreRate(EvaluationModel):
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)

    @property
    def value(self) -> float | None:
        return self.numerator / self.denominator if self.denominator else None


class CaseScore(EvaluationModel):
    candidate_id: str
    paper_id: str
    task_kind: str
    execution: str
    reviewed: bool
    status_match: bool | None = None
    matched_required_claim_ids: list[str] = Field(default_factory=list)
    missed_required_claim_ids: list[str] = Field(default_factory=list)
    retrieved_evidence_ids: list[str] = Field(default_factory=list)
    correct_claims: int = 0
    output_claims: int = 0
    citation_correct: int = 0
    citation_evaluated: int = 0
    panel_aligned: int = 0
    panel_evaluated: int = 0
    complete: bool | None = None
    primary_error: ErrorCategory | None = None
    secondary_errors: list[ErrorCategory] = Field(default_factory=list)
    rationale: str = "尚未独立评价。"


class ScoreReport(EvaluationModel):
    schema_version: Literal["qa-score-v1"] = "qa-score-v1"
    dataset_id: str
    dataset_sha256: str
    run_id: str
    reference_status: str
    review_kind: str | None
    scope: str = "相对版本化参考集的评价；AI 暂定参考与专家评测分别标识。"
    metrics: dict[str, ScoreRate]
    by_task: dict[str, dict[str, ScoreRate]]
    error_counts: dict[str, int]
    error_denominator: int
    optimization_priority: list[str]
    cases: list[CaseScore]
