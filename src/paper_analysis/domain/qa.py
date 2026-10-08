"""单篇文献问答协议；证据定位由后端提供，不接受模型生成的路径。"""
from typing import Literal
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from paper_analysis.domain.execution import (
    AnalysisIntensity,
    ExecutionPolicyRequest,
    ExecutionSummary,
    ResolvedPolicy,
)
from paper_analysis.domain.models import ClaimEvidence
from paper_analysis.domain.models import FactCheckBatch
from paper_analysis.domain.quality import QualityReport


class QuestionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    figure: str | None = Field(default=None, pattern=r"^(?:Figure |Fig\.? |图)?[Ss]?\d+$")
    panel: str | None = Field(default=None, pattern=r"^[a-zA-Z]$")
    max_followups: int = Field(default=2, ge=0, le=2)
    policy: ExecutionPolicyRequest | None = None
    # 允许 multipart 客户端不构造嵌套 JSON；服务层会将这些覆盖值归一化到 policy。
    intensity: AnalysisIntensity | None = None
    token_budget: int | None = Field(default=None, ge=256, le=10_000_000)
    max_calls: int | None = Field(default=None, ge=1, le=10_000)
    max_output_tokens: int | None = Field(default=None, ge=64, le=100_000)
    timeout_seconds: float | None = Field(default=None, gt=0, le=86_400)
    max_figures: int | None = Field(default=None, ge=0, le=100)
    max_visual_reviews: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def panel_requires_figure(self) -> "QuestionRequest":
        if self.panel and not self.figure:
            raise ValueError("指定子图时必须同时指定图号。")
        return self

    def execution_policy_request(self) -> ExecutionPolicyRequest:
        base = self.policy or ExecutionPolicyRequest(max_followups=self.max_followups)
        updates = {
            name: value
            for name, value in {
                "intensity": self.intensity,
                "token_budget": self.token_budget,
                "max_calls": self.max_calls,
                "max_output_tokens": self.max_output_tokens,
                "timeout_seconds": self.timeout_seconds,
                "max_figures": self.max_figures,
                "max_visual_reviews": self.max_visual_reviews,
            }.items()
            if value is not None
        }
        # policy 显式提供时尊重其中的 max_followups；旧 multipart 请求继续沿用 0–2。
        if self.policy is None or self.max_followups != 2:
            updates["max_followups"] = self.max_followups
        return base.model_copy(update=updates)


class EvidenceLocation(BaseModel):
    evidence_id: str
    kind: Literal["text", "caption", "vision"]
    page: int = Field(ge=1)
    block_id: str | None = None
    bbox: list[float] = Field(default_factory=list)
    figure: str | None = None
    panel: str | None = None
    excerpt: str
    image_pages: list[int] = Field(default_factory=list)


class AnswerClaim(ClaimEvidence):
    basis: Literal["text", "visual"]


class AnswerDraft(BaseModel):
    claims: list[AnswerClaim] = Field(default_factory=list, max_length=12)
    uncertainties: list[str] = Field(default_factory=list)
    sufficient: bool = False
    search_terms: list[str] = Field(default_factory=list, max_length=6)
    evidence_gaps: list[Literal["methods", "controls", "statistics", "results", "vision"]] = Field(default_factory=list, max_length=5)


class VisualClaimCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str
    statement: str
    verdict: Literal["supported", "conflicting", "unverifiable"]
    observation: str = Field(min_length=1, max_length=1500)
    rationale: str = Field(min_length=1, max_length=1500)


class VisualCheckBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checks: list[VisualClaimCheck] = Field(default_factory=list, max_length=12)


class VisualReview(BaseModel):
    status: Literal["reviewed", "failed", "budget_exhausted", "no_images"]
    failure_reason: Literal[
        "no_images", "budget_exhausted", "deadline_exceeded", "timeout", "http_error", "parse_error", "provider_error"
    ] | None = None
    checks: list[VisualClaimCheck] = Field(default_factory=list)
    image_sha256: list[str] = Field(default_factory=list)
    reused: bool = False
    calls_used: int = 0


class QuestionRound(BaseModel):
    index: int
    evidence: list[EvidenceLocation]
    new_evidence_ids: list[str] = Field(default_factory=list)
    draft: AnswerDraft | None = None
    checks: FactCheckBatch | None = None
    quality: QualityReport | None = None
    visual_review: VisualReview | None = None
    elapsed_seconds: float = 0
    error: str | None = None


class AnswerResponse(BaseModel):
    schema_version: str = "qa-v2"
    id: UUID = Field(default_factory=uuid4)
    request: QuestionRequest
    status: Literal["answered", "partial", "refused"]
    answer: str
    claims: list[AnswerClaim] = Field(default_factory=list)
    evidence: list[EvidenceLocation] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    visual_status: Literal["not_requested", "succeeded", "failed"] = "not_requested"
    visual_checks: list[VisualClaimCheck] = Field(default_factory=list)
    followups: int = Field(default=0, ge=0, le=2)
    quality: QualityReport
    policy: ResolvedPolicy | None = None
    execution: ExecutionSummary | None = None
    validation_scope: str = "自动证据定位与模型核验；未经领域专家效果验证。"
    stop_reason: str = "completed"
    document_sha256: str = ""


class QuestionJob(BaseModel):
    batch_id: UUID | None = None
    conversation_id: UUID | None = None
    parent_turn_id: UUID | None = None
    id: UUID = Field(default_factory=uuid4)
    request: QuestionRequest
    filename: str
    document_sha256: str
    status: Literal["queued", "running", "completed", "failed", "timed_out", "cancelled"] = "queued"
    stage: str = "等待执行"
    attempt: int = 1
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    policy: ResolvedPolicy | None = None


class QuestionAudit(BaseModel):
    schema_version: str = "qa-v2"
    job_id: UUID
    attempt: int
    document_sha256: str
    execution_kind: Literal["real_call", "offline_test"]
    model: str = "unknown"
    vision_model: str | None = None
    vision_configuration_fingerprint: str | None = None
    parser_version: str = ""
    runtime_fingerprint: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    parse_cache_hit: bool = False
    parse_seconds: float = 0
    total_seconds: float = 0
    rounds: list[QuestionRound] = Field(default_factory=list)
    stop_reason: str = "running"
    expert_evaluation: Literal["not_evaluated"] = "not_evaluated"
    policy: ResolvedPolicy | None = None
    execution: ExecutionSummary | None = None
