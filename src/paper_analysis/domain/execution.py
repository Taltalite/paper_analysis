"""执行策略、模型能力、调用审计与预算结果的公共协议。

这些模型只描述边界和事实，不依赖 CrewAI、HTTP 客户端或具体供应商 SDK。
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SCHEMA_VERSION = "execution-v1"
POLICY_VERSION = "policy-v1"


class AnalysisIntensity(StrEnum):
    LIGHT = "light"
    STANDARD = "standard"
    DEEP = "deep"


class StopReason(StrEnum):
    COMPLETED = "completed"
    NO_NEW_EVIDENCE = "no_new_evidence"
    TARGET_UNRESOLVED = "target_unresolved"
    EVIDENCE_UNAVAILABLE = "evidence_unavailable"
    ROUND_LIMIT = "round_limit"
    TOKEN_BUDGET_EXHAUSTED = "token_budget_exhausted"
    CALL_BUDGET_EXHAUSTED = "call_budget_exhausted"
    DEADLINE_EXCEEDED = "deadline_exceeded"
    CANCELLED = "cancelled"
    PROVIDER_ERROR = "provider_error"
    INVALID_OUTPUT = "invalid_output"
    VERIFICATION_FAILED = "verification_failed"


class CapabilityStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    UNSUPPORTED = "unsupported"


class CallStatus(StrEnum):
    RESERVED = "reserved"
    SENT = "sent"
    SUCCEEDED = "succeeded"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"
    INVALID_OUTPUT = "invalid_output"
    NOT_SENT = "not_sent"
    CACHE_HIT = "cache_hit"


class UsageSource(StrEnum):
    PROVIDER = "provider"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"
    CACHE = "cache"
    NOT_SENT = "not_sent"
    NOT_RECORDED = "not_recorded"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ExecutionPolicyRequest(StrictModel):
    """请求方可提供的策略覆盖；None 表示使用强度档位默认值。"""

    intensity: AnalysisIntensity = AnalysisIntensity.STANDARD
    report_followups: int | None = Field(default=None, ge=0, le=2)
    token_budget: int | None = Field(default=None, ge=256, le=10_000_000)
    max_calls: int | None = Field(default=None, ge=1, le=10_000)
    max_output_tokens: int | None = Field(default=None, ge=64, le=100_000)
    timeout_seconds: float | None = Field(default=None, gt=0, le=86_400)
    max_followups: int | None = Field(default=None, ge=0, le=10)
    max_figures: int | None = Field(default=None, ge=0, le=100)
    max_visual_reviews: int | None = Field(default=None, ge=0, le=100)


class ExecutionPolicy(StrictModel):
    schema_version: str = SCHEMA_VERSION
    intensity: AnalysisIntensity = AnalysisIntensity.STANDARD
    report_followups: int = Field(default=0, ge=0, le=2)
    token_budget: int = Field(ge=256, le=10_000_000)
    max_calls: int = Field(ge=1, le=10_000)
    max_output_tokens: int = Field(ge=64, le=100_000)
    timeout_seconds: float = Field(gt=0, le=86_400)
    max_followups: int = Field(ge=0, le=10)
    max_figures: int = Field(ge=0, le=100)
    max_visual_reviews: int = Field(ge=0, le=100)


_INTENSITY_DEFAULTS: dict[AnalysisIntensity, dict[str, int | float]] = {
    AnalysisIntensity.LIGHT: {
        "token_budget": 12_000,
        "max_calls": 8,
        "max_output_tokens": 2_048,
        "timeout_seconds": 180.0,
        "max_followups": 0,
        "max_figures": 2,
        "max_visual_reviews": 1,
    },
    AnalysisIntensity.STANDARD: {
        "token_budget": 30_000,
        "max_calls": 16,
        "max_output_tokens": 4_096,
        "timeout_seconds": 420.0,
        "max_followups": 1,
        "max_figures": 4,
        "max_visual_reviews": 2,
    },
    AnalysisIntensity.DEEP: {
        "token_budget": 60_000,
        "max_calls": 32,
        "max_output_tokens": 6_144,
        "timeout_seconds": 720.0,
        "max_followups": 2,
        "max_figures": 6,
        "max_visual_reviews": 2,
    },
}


DEFAULT_SERVER_LIMITS = ExecutionPolicy(
    intensity=AnalysisIntensity.STANDARD,
    token_budget=120_000,
    max_calls=128,
    max_output_tokens=12_000,
    timeout_seconds=900.0,
    max_followups=10,
    max_figures=12,
    max_visual_reviews=8,
    report_followups=2,
)


class ResolvedPolicy(StrictModel):
    schema_version: str = SCHEMA_VERSION
    requested: ExecutionPolicyRequest
    server_limits: ExecutionPolicy
    effective: ExecutionPolicy
    policy_version: str = POLICY_VERSION
    configuration_fingerprint: str

    @classmethod
    def resolve(
        cls,
        requested: ExecutionPolicyRequest | None = None,
        *,
        server_limits: ExecutionPolicy = DEFAULT_SERVER_LIMITS,
    ) -> "ResolvedPolicy":
        request = requested or ExecutionPolicyRequest()
        defaults = _INTENSITY_DEFAULTS[request.intensity]
        values: dict[str, int | float | AnalysisIntensity] = {"intensity": request.intensity}
        for name in (
            "token_budget",
            "max_calls",
            "max_output_tokens",
            "timeout_seconds",
            "max_followups",
            "max_figures",
            "max_visual_reviews",
        ):
            requested_value = getattr(request, name)
            candidate = defaults[name] if requested_value is None else requested_value
            values[name] = min(candidate, getattr(server_limits, name))
        effective = ExecutionPolicy(**values)
        effective.report_followups = min(request.report_followups or 0, server_limits.report_followups)
        fingerprint_payload = {
            "policy_version": POLICY_VERSION,
            "requested": request.model_dump(mode="json"),
            "server_limits": server_limits.model_dump(mode="json"),
            "effective": effective.model_dump(mode="json"),
        }
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return cls(
            requested=request,
            server_limits=server_limits,
            effective=effective,
            configuration_fingerprint=fingerprint,
        )


class ModelCapabilities(StrictModel):
    schema_version: str = SCHEMA_VERSION
    provider: str
    model: str
    endpoint_id: str
    text: CapabilityStatus = CapabilityStatus.UNVERIFIED
    image: CapabilityStatus = CapabilityStatus.UNSUPPORTED
    structured_output: CapabilityStatus = CapabilityStatus.UNVERIFIED
    usage: CapabilityStatus = CapabilityStatus.UNVERIFIED
    native_reasoning_effort: CapabilityStatus = CapabilityStatus.UNSUPPORTED
    output_token_limits: CapabilityStatus = CapabilityStatus.UNVERIFIED
    timeout: CapabilityStatus = CapabilityStatus.UNVERIFIED
    native_parameters: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TokenUsage(StrictModel):
    """None 表示供应商未返回该项；0 只表示供应商明确返回零。"""

    input: int | None = Field(default=None, ge=0)
    output: int | None = Field(default=None, ge=0)
    total: int | None = Field(default=None, ge=0)
    cached: int | None = Field(default=None, ge=0)
    reasoning: int | None = Field(default=None, ge=0)
    estimated: bool = False
    reserved: int | None = Field(default=None, ge=0)
    unknown: bool = False

    @model_validator(mode="after")
    def validate_total(self) -> "TokenUsage":
        if self.total is not None and self.input is not None and self.output is not None:
            if self.total < self.input + self.output:
                raise ValueError("total 不能小于 input + output。")
        if self.unknown and self.total is not None:
            raise ValueError("unknown 用量不能同时提供 total。")
        return self


class CallRecord(StrictModel):
    schema_version: str = SCHEMA_VERSION
    call_id: str = Field(min_length=1, max_length=128)
    job_id: str = Field(min_length=1, max_length=128)
    attempt: int = Field(ge=1)
    stage: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=200)
    endpoint_id: str = Field(min_length=1, max_length=300)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = None
    status: CallStatus = CallStatus.RESERVED
    usage_source: UsageSource = UsageSource.NOT_RECORDED
    usage: TokenUsage | None = None
    reservation: int = Field(default=0, ge=0)


class ExecutionSummary(StrictModel):
    schema_version: str = SCHEMA_VERSION
    actual_usage: TokenUsage = Field(default_factory=TokenUsage)
    estimated_usage: TokenUsage = Field(default_factory=TokenUsage)
    unknown_usage: bool = False
    call_count: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    cache_hits: int = Field(default=0, ge=0)
    budget: ExecutionPolicy | None = None
    elapsed_seconds: float = Field(default=0, ge=0)
    stop_reason: StopReason | str = StopReason.COMPLETED
    calls: list[CallRecord] = Field(default_factory=list)


class CoverageSet(StrictModel):
    sections: list[str] = Field(default_factory=list)
    figures: list[str] = Field(default_factory=list)
    panels: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)


class CoverageReport(StrictModel):
    schema_version: str = SCHEMA_VERSION
    candidate: CoverageSet = Field(default_factory=CoverageSet)
    selected: CoverageSet = Field(default_factory=CoverageSet)
    read: CoverageSet = Field(default_factory=CoverageSet)
    verified: CoverageSet = Field(default_factory=CoverageSet)
    skipped: dict[str, list[str]] = Field(default_factory=dict)

