from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, computed_field


class QualityIssue(BaseModel):
    code: str
    severity: Literal["warning", "major", "critical"] = "major"
    location: str
    claim_id: str = ""
    message: str
    action: str = "请核对原文证据后重新确认。"


class ReportBinding(BaseModel):
    location: str
    claim_ids: list[str] = Field(default_factory=list)
    released: bool = False


class QualityReport(BaseModel):
    version: str = "qc-v1"
    status: Literal["passed", "needs_review", "blocked"] = "needs_review"
    document_fingerprint: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    expected_claims: int = 0
    invalid_claims: int = 0
    checked_claims: int = 0
    accepted_claim_ids: list[str] = Field(default_factory=list)
    issues: list[QualityIssue] = Field(default_factory=list)
    bindings: list[ReportBinding] = Field(default_factory=list)
    scope: str = "主张对应关系、证据引用定位和报告交付；不代表独立语义正确性或医学质量认证。"

    @computed_field
    @property
    def coverage(self) -> float:
        return self.checked_claims / self.expected_claims if self.expected_claims else 0.0
