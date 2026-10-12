"""按论文独立使用 standard 默认额度，聚合固定问题的生产问答基线。"""
from __future__ import annotations

from pathlib import Path

from paper_analysis.adapters.storage.qa_store import atomic_json
from paper_analysis.domain.execution import ResolvedPolicy
from paper_analysis.services.qa_evaluation import (
    EvaluationManifest, QuestionCandidate, run_candidates, summarize_checks,
)
from paper_analysis.services.reference_evaluation import file_sha256


async def run_paper_batches(manifest: Path, root: Path, *, real: bool = False,
                            max_followups: int = 0) -> EvaluationManifest:
    if any((root / name).exists() for name in ("baseline_manifest.json", "manifest.json", "questions")):
        raise ValueError("基线目录已有记录，请使用新目录以保留历史运行。")
    candidates = [QuestionCandidate.model_validate_json(line) for line in manifest.read_text().splitlines() if line.strip()]
    if not candidates or len({c.id for c in candidates}) != len(candidates):
        raise ValueError("基线问题清单不能为空或包含重复 ID。")
    groups: dict[str, set[str]] = {}
    for case in candidates:
        if case.paper is None:
            raise ValueError("论文基线中的所有问题必须绑定 PDF。")
        groups.setdefault(case.paper.sha256, set()).add(case.id)
    policy = ResolvedPolicy.resolve().effective
    report = EvaluationManifest(candidate_manifest_sha256=file_sha256(manifest),
        scope="生产问答固定基线；每篇论文独立共享 standard 默认额度；独立科学评价另列。",
        run_settings={"token_budget_per_paper": policy.token_budget,
                      "max_output_tokens": policy.max_output_tokens,
                      "max_calls_per_paper": policy.max_calls,
                      "timeout_seconds": policy.timeout_seconds,
                      "max_followups": max_followups,
                      "paper_batches": len(groups)})
    for identifiers in groups.values():
        results = await run_candidates(manifest, root, ids=identifiers, real=real,
            max_followups=max_followups, token_budget=policy.token_budget, max_calls=policy.max_calls)
        report.results.extend(results)
        report.engineering_summary = summarize_checks(report.results)
        atomic_json(root / "baseline_manifest.json", report)
    return report
