"""运行候选而非打专家分；真实调用记录与工程门禁分别报告。"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4
from pathlib import Path

from pydantic import BaseModel, Field
from paper_analysis.domain.execution import ExecutionPolicyRequest

from paper_analysis.adapters.storage.qa_store import atomic_json
from paper_analysis.domain.qa import QuestionRequest
from paper_analysis.services.question_answer_service import build_question_answer_service
from paper_analysis.services.question_jobs import QuestionJobs


class CandidatePaper(BaseModel):
    source_path: str
    sha256: str


class QuestionCandidate(BaseModel):
    id: str
    question: str
    paper: CandidatePaper | None = None
    figure: str | None = None
    panel: str | None = None
    disable_vision: bool = False


class CandidateRun(BaseModel):
    candidate_id: str
    execution: str
    answer_id: str | None = None
    answer_status: str | None = None
    visual_status: str | None = None
    reason: str | None = None
    audit_path: str | None = None
    engineering_checks: dict[str, bool | str] = Field(default_factory=dict)
    expert_evaluation: str = "not_evaluated"


class EvaluationManifest(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    results: list[CandidateRun] = Field(default_factory=list)
    scope: str = "工程运行记录；不包含人工正确性评分。"
    engineering_summary: dict[str, dict[str, int | float | None]] = Field(default_factory=dict)


def summarize_checks(results: list[CandidateRun]) -> dict[str, dict[str, int | float | None]]:
    """N/A 和未执行不进入通过率分母，避免把空集合报告为成功。"""
    keys = sorted({key for result in results for key in result.engineering_checks})
    summary = {}
    for key in keys:
        values = [result.engineering_checks.get(key) for result in results]
        passed = sum(value is True for value in values)
        failed = sum(value is False for value in values)
        summary[key] = {"passed": passed, "failed": failed,
                        "not_applicable": sum(value == "not_applicable" for value in values),
                        "not_evaluated": sum(value is None for value in values),
                        "pass_rate": passed / (passed + failed) if passed + failed else None}
    return summary


async def run_candidates(manifest: Path, root: Path, *, ids: set[str] | None = None,
                         max_followups: int = 0, real: bool = False, token_budget: int = 60000, max_calls: int = 32) -> list[CandidateRun]:
    candidates = [QuestionCandidate.model_validate_json(line) for line in manifest.read_text().splitlines() if line.strip()]
    known_ids = {case.id for case in candidates}
    if len(known_ids) != len(candidates) or (ids and not ids <= known_ids):
        raise ValueError("候选 ID 重复或筛选包含未知 ID。")
    report = EvaluationManifest()
    results = report.results
    for case in candidates:
        if ids and case.id not in ids:
            continue
        record = CandidateRun(candidate_id=case.id, execution="not_called")
        results.append(record)
        if case.paper is None:
            record.reason = "候选尚未绑定论文。"
        elif not Path(case.paper.source_path).exists():
            record.reason = "本地 PDF 不存在。"
        else:
            source = Path(case.paper.source_path)
            content = source.read_bytes()
            if hashlib.sha256(content).hexdigest() != case.paper.sha256:
                record.reason = "PDF 指纹不匹配，未调用模型。"
            elif not real:
                record.reason = "准备检查通过；未指定 --real，不调用模型。"
            else:
                await _execute_candidate(case, root, content, max_followups, record, report.run_id, token_budget, max_calls)
        report.engineering_summary = summarize_checks(results)
        atomic_json(root / f"manifest-{report.run_id}.json", report)
        atomic_json(root / "manifest.json", report)
    if not results:
        atomic_json(root / f"manifest-{report.run_id}.json", report)
        atomic_json(root / "manifest.json", report)
    return results


async def _execute_candidate(case: QuestionCandidate, root: Path, content: bytes,
                             max_followups: int, record: CandidateRun, batch_id: UUID, token_budget: int, max_calls: int) -> None:
    try:
        request = QuestionRequest(question=case.question, figure=case.figure, panel=case.panel,
                                  max_followups=max_followups, policy=ExecutionPolicyRequest(token_budget=token_budget, max_calls=max_calls, max_followups=max_followups))
        service = build_question_answer_service(root / "questions", disable_vision=case.disable_vision)
    except Exception as exc:
        record.execution, record.reason = "configuration_failed", type(exc).__name__
        return
    service.batch_id = batch_id
    manager = QuestionJobs(service)
    job = None
    try:
        await manager.start()
        job = manager.submit(filename=Path(case.paper.source_path).name, content=content, request=request)
        record.answer_id = str(job.id)
        record.audit_path = str(service.store.directory(job.id) / "audit-1.json")
        record.execution = "real_configuration_attempted"
        await manager.tasks[job.id]
        answer = service.get(job.id)
        record.answer_status, record.visual_status = answer.status, answer.visual_status
        audit = service.audit(job.id)
        record.execution = "real_runtime_executed" if audit.rounds else "no_generation_early_refusal"
        ids_available = {e.evidence_id for e in answer.evidence}
        record.engineering_checks = {
            "bounded_rounds": len(audit.rounds) <= max_followups + 1,
            "same_document": answer.document_sha256 == case.paper.sha256,
            "citations_resolve": all(set(c.evidence_ids) <= ids_available for c in answer.claims),
            "no_fake_visual_success": not case.disable_vision or answer.visual_status != "succeeded",
            "audit_saved": Path(record.audit_path).is_file(),
            "visual_claims_reviewed": all(any(check.claim_id == claim.claim_id and check.statement == claim.statement
                and check.verdict == "supported" for check in answer.visual_checks)
                for claim in answer.claims if claim.basis == "visual"),
            "visual_review_budget": all(r.visual_review.calls_used <= 2 for r in audit.rounds if r.visual_review),
            "no_model_error": answer.stop_reason not in {"model_error", "provider_error"} and not any(r.error for r in audit.rounds)
                and not any(r.visual_review and r.visual_review.failure_reason in {"timeout", "http_error", "parse_error", "provider_error"} for r in audit.rounds),
            "visual_review_completed": all(r.visual_review.status == "reviewed" for r in audit.rounds if r.visual_review)
                if any(r.visual_review for r in audit.rounds) else "not_applicable",
            "actual_usage_recorded": answer.execution.actual_usage.total is not None if answer.execution and answer.execution.call_count else "not_applicable",
        }
    except Exception as exc:
        record.execution, record.reason = "execution_failed", type(exc).__name__
        if job:
            record.reason = service.store.get(job.id).error or type(exc).__name__
    finally:
        await manager.close()
