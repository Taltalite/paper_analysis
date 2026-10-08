from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from paper_analysis.domain.execution import ExecutionPolicyRequest, ExecutionSummary, ResolvedPolicy
from paper_analysis.domain.enums import AnalysisMode, DocumentKind, JobStatus
from paper_analysis.domain.models import FigureMetadata
from paper_analysis.domain.quality import QualityReport
from paper_analysis.domain.research import ResearchProducts


class UploadAnalysisRequest(BaseModel):
    mode: AnalysisMode = AnalysisMode.RESEARCH_PAPER
    filename: str
    document_kind: DocumentKind
    llm_provider: str = "default"
    llm_model: str = "default"
    options: dict[str, Any] = Field(default_factory=dict)
    policy: ExecutionPolicyRequest | None = None


class FileAnalysisRequest(BaseModel):
    input_path: str
    output_markdown_path: str
    output_json_path: str
    mode: AnalysisMode = AnalysisMode.RESEARCH_PAPER
    policy: ExecutionPolicyRequest | None = None


class ParsedDocument(BaseModel):
    title: str = ""
    raw_text: str = ""
    markdown: str = ""
    sections: dict[str, str] = Field(default_factory=dict)
    section_order: list[str] = Field(default_factory=list)
    figures: list[FigureMetadata] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalysisArtifact(BaseModel):
    markdown_report_path: str | None = None
    json_report_path: str | None = None
    parsed_markdown_path: str | None = None
    log_path: str | None = None


class AnalysisJob(BaseModel):
    attempt: int = Field(default=1, ge=1)
    document_sha256: str = ""
    id: UUID = Field(default_factory=uuid4)
    status: JobStatus = JobStatus.PENDING
    mode: AnalysisMode
    document_kind: DocumentKind
    filename: str
    input_path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_message: str | None = None
    artifact: AnalysisArtifact = Field(default_factory=AnalysisArtifact)
    quality: QualityReport | None = None
    policy: ResolvedPolicy | None = None
    execution: ExecutionSummary | None = None


class AnalysisResult(BaseModel):
    schema_version: str = "analysis-v2"
    title: str = ""
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    markdown_report: str = ""
    structured_data: dict[str, Any] = Field(default_factory=dict)
    quality: QualityReport | None = None
    policy: ResolvedPolicy | None = None
    execution: ExecutionSummary | None = None
    research_products: ResearchProducts | None = None


class AnalysisExecution(BaseModel):
    document: ParsedDocument
    result: AnalysisResult


class HealthResponse(BaseModel):
    status: str = "ok"


class MarkdownReportResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    markdown_report: str
    parsed_markdown: str | None = None
    quality: QualityReport | None = None
    policy: ResolvedPolicy | None = None
    execution: ExecutionSummary | None = None


class JobProgressStep(BaseModel):
    key: str
    label: str
    status: str


class JobProgressResponse(BaseModel):
    job: AnalysisJob
    current_stage: str
    progress_percent: int
    summary_message: str
    recent_logs: list[str] = Field(default_factory=list)
    steps: list[JobProgressStep] = Field(default_factory=list)


class ArtifactContentResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    artifact: AnalysisArtifact
    markdown_report: str | None = None
    parsed_markdown: str | None = None
    json_report: dict[str, Any] | None = None
    quality: QualityReport | None = None
    policy: ResolvedPolicy | None = None
    execution: ExecutionSummary | None = None
