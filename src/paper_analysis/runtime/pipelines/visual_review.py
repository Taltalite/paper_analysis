"""每题独立预算与复用；只让直接看图核验通过的视觉主张交付。"""
from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import httpx

from paper_analysis.adapters.llm.visual_check import VisualClaimChecker
from paper_analysis.domain.qa import AnswerClaim, QuestionRequest, VisualReview
from paper_analysis.domain.quality import QualityIssue, QualityReport
from paper_analysis.runtime.budget import BudgetExceededError, BudgetLedger, DeadlineExceededError


class VisualReviewSession:
    def __init__(self, checker: VisualClaimChecker, max_calls: int = 2) -> None:
        self.checker, self.max_calls = checker, max_calls
        self.calls = 0
        self.cache: dict[str, VisualReview] = {}

    def review(self, *, request: QuestionRequest, claims: list[AnswerClaim],
               image_paths: list[Path], execution_context: BudgetLedger | None = None) -> VisualReview:
        try:
            if not image_paths or len(image_paths) > 4 or not all(p.is_file() for p in image_paths):
                return VisualReview(status="no_images", failure_reason="no_images", calls_used=self.calls)
            fingerprints = [hashlib.sha256(p.read_bytes()).hexdigest() for p in image_paths]
            key = request.model_dump_json() + str(fingerprints) + "".join(c.model_dump_json() for c in claims)
            if key in self.cache:
                return self.cache[key].model_copy(deep=True, update={"reused": True, "calls_used": self.calls})
            if self.calls >= self.max_calls:
                return VisualReview(status="budget_exhausted", failure_reason="budget_exhausted",
                                    image_sha256=fingerprints, calls_used=self.calls)
            self.calls += 1
            if "execution_context" in inspect.signature(self.checker.check).parameters or any(
                parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in inspect.signature(self.checker.check).parameters.values()
            ):
                result = self.checker.check(request=request, claims=claims, image_paths=image_paths,
                                            execution_context=execution_context)
            else:
                result = self.checker.check(request=request, claims=claims, image_paths=image_paths)
            expected = {c.claim_id: c.statement for c in claims}
            actual = {c.claim_id: c.statement for c in result.checks}
            if len(result.checks) != len(expected) or actual != expected:
                raise ValueError("视觉核验漏项、重复或主张不一致。")
            review = VisualReview(status="reviewed", checks=result.checks,
                                  image_sha256=fingerprints, calls_used=self.calls)
            self.cache[key] = review.model_copy(deep=True)
            return review
        except BudgetExceededError:
            return VisualReview(status="budget_exhausted", failure_reason="budget_exhausted", calls_used=self.calls)
        except DeadlineExceededError:
            return VisualReview(status="failed", failure_reason="deadline_exceeded", calls_used=self.calls)
        except (TimeoutError, httpx.TimeoutException):
            return VisualReview(status="failed", failure_reason="timeout", calls_used=self.calls)
        except httpx.HTTPStatusError:
            return VisualReview(status="failed", failure_reason="http_error", calls_used=self.calls)
        except ValueError:
            return VisualReview(status="failed", failure_reason="parse_error", calls_used=self.calls)
        except Exception:
            # 不把供应商错误正文或密钥写入审计。
            return VisualReview(status="failed", failure_reason="provider_error", calls_used=self.calls)


def enforce_visual_review(quality: QualityReport, claims: list[AnswerClaim], review: VisualReview) -> None:
    checks = {check.claim_id: check for check in review.checks}
    for claim in claims:
        check = checks.get(claim.claim_id)
        if review.status == "reviewed" and check and check.verdict == "supported":
            continue
        quality.accepted_claim_ids = [cid for cid in quality.accepted_claim_ids if cid != claim.claim_id]
        reason = (check.rationale + "；实际观察：" + check.observation) if check else "直接看图核验未完成，不能交付视觉主张。"
        quality.issues.append(QualityIssue(code="qa_visual_review", location=claim.claim_id,
                                          claim_id=claim.claim_id, message=reason))
    quality.status = "blocked" if not quality.accepted_claim_ids else ("needs_review" if quality.issues else "passed")
    for binding in quality.bindings:
        binding.claim_ids = [cid for cid in binding.claim_ids if cid in quality.accepted_claim_ids]
        binding.released = bool(binding.claim_ids)
