"""运行候选而非打专家分；真实调用记录与工程门禁分别报告。"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4
from pathlib import Path

from pydantic import BaseModel, Field

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
    engineering_checks: dict[str, bool] = Field(default_factory=dict)
    expert_evaluation: str = "not_evaluated"


class EvaluationManifest(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    results: list[CandidateRun] = Field(default_factory=list)
    scope: str = "工程运行记录；不包含人工正确性评分。"


async def run_candidates(manifest: Path, root: Path, *, ids: set[str] | None = None,
                         max_followups: int = 0, real: bool = False) -> list[CandidateRun]:
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
                await _execute_candidate(case, root, content, max_followups, record)
        atomic_json(root / f"manifest-{report.run_id}.json", report)
        atomic_json(root / "manifest.json", report)
    if not results:
        atomic_json(root / f"manifest-{report.run_id}.json", report)
        atomic_json(root / "manifest.json", report)
    return results


async def _execute_candidate(case: QuestionCandidate, root: Path, content: bytes,
                             max_followups: int, record: CandidateRun) -> None:
    try:
        request = QuestionRequest(question=case.question, figure=case.figure, panel=case.panel,
                                  max_followups=max_followups)
        service = build_question_answer_service(root / "questions", disable_vision=case.disable_vision)
    except Exception as exc:
        record.execution, record.reason = "configuration_failed", type(exc).__name__
        return
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
        }
    except Exception as exc:
        record.execution, record.reason = "execution_failed", type(exc).__name__
        if job:
            record.reason = service.store.get(job.id).error or type(exc).__name__
    finally:
        await manager.close()
