"""单篇文献问答协议；证据定位由后端提供，不接受模型生成的路径。"""
from typing import Literal
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from paper_analysis.domain.models import ClaimEvidence
from paper_analysis.domain.models import FactCheckBatch
from paper_analysis.domain.quality import QualityReport


class QuestionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    figure: str | None = Field(default=None, pattern=r"^(?:Figure |Fig\.? |图)?[Ss]?\d+$")
    panel: str | None = Field(default=None, pattern=r"^[a-zA-Z]$")
    max_followups: int = Field(default=2, ge=0, le=2)

    @model_validator(mode="after")
    def panel_requires_figure(self) -> "QuestionRequest":
        if self.panel and not self.figure:
            raise ValueError("指定子图时必须同时指定图号。")
        return self


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
    evidence_gaps: list[Literal["methods", "controls", "statistics", "results"]] = Field(default_factory=list, max_length=4)


class QuestionRound(BaseModel):
    index: int
    evidence: list[EvidenceLocation]
    new_evidence_ids: list[str] = Field(default_factory=list)
    draft: AnswerDraft | None = None
    checks: FactCheckBatch | None = None
    quality: QualityReport | None = None
    elapsed_seconds: float = 0
    error: str | None = None


class AnswerResponse(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    request: QuestionRequest
    status: Literal["answered", "partial", "refused"]
    answer: str
    claims: list[AnswerClaim] = Field(default_factory=list)
    evidence: list[EvidenceLocation] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    visual_status: Literal["not_requested", "succeeded", "failed"] = "not_requested"
    followups: int = Field(default=0, ge=0, le=2)
    quality: QualityReport
    validation_scope: str = "自动证据定位与模型核验；未经领域专家效果验证。"
    stop_reason: str = "completed"
    document_sha256: str = ""


class QuestionJob(BaseModel):
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


class QuestionAudit(BaseModel):
    job_id: UUID
    attempt: int
    document_sha256: str
    execution_kind: Literal["real_call", "offline_test"]
    model: str = "unknown"
    vision_model: str | None = None
    parser_version: str = ""
    runtime_fingerprint: str = ""
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    parse_cache_hit: bool = False
    parse_seconds: float = 0
    total_seconds: float = 0
    rounds: list[QuestionRound] = Field(default_factory=list)
    stop_reason: str = "running"
    expert_evaluation: Literal["not_evaluated"] = "not_evaluated"
