"""独立主张评价的可重复评分与错误汇总；不把自检或关键词匹配当正确性。"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from pathlib import Path

from paper_analysis.adapters.parser.reference_source import PdfSourceInspector, PyMuPdfSourceInspector
from paper_analysis.adapters.storage.qa_store import atomic_json
from paper_analysis.domain.evaluation import (
    CaseReview, CaseScore, ReferenceCase, ReferenceDataset, ReviewBundle, ScoreRate, ScoreReport,
)
from paper_analysis.domain.qa import AnswerResponse, QuestionAudit
from paper_analysis.services.qa_evaluation import EvaluationManifest


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_quote(value: str) -> str:
    value = re.sub(r"(?<=\w)-\s+(?=\w)", "", value)
    value = unicodedata.normalize("NFKC", value.replace("\u00ad", ""))
    return " ".join(value.split()).casefold()


def load_reference(path: Path) -> ReferenceDataset:
    return ReferenceDataset.model_validate_json(path.read_text(encoding="utf-8"))


def validate_sources(dataset: ReferenceDataset, source_reader: PdfSourceInspector | None = None) -> dict[str, int]:
    """确定性检查文件绑定、引文与坐标；视觉语义仍依赖独立阅读原图。"""
    reader = source_reader or PyMuPdfSourceInspector()
    quotes = visuals = 0
    for paper_id, paper in dataset.papers.items():
        source = Path(paper.source_path)
        if file_sha256(source) != paper.sha256:
            raise ValueError(f"{paper_id}：PDF 指纹不匹配。")
        if reader.page_count(source) != paper.page_count:
            raise ValueError(f"{paper_id}：页数不匹配。")
        for case in (c for c in dataset.cases if c.paper_id == paper_id):
            for evidence in case.gold_evidence:
                text = reader.region_text(source, evidence.pdf_page_1_based, evidence.bbox)
                if evidence.verbatim_quote:
                    if normalize_quote(evidence.verbatim_quote) not in normalize_quote(text):
                        raise ValueError(f"{case.candidate_id}/{evidence.evidence_id}：定位区域未找到引文。")
                    quotes += 1
                else:
                    visuals += 1
    return {"papers": len(dataset.papers), "cases": len(dataset.cases), "quotes_validated": quotes, "visual_regions": visuals}


def prepare_candidates(dataset: ReferenceDataset, output: Path) -> None:
    """只给被测系统问题和 PDF 绑定，参考答案及证据不进入运行清单。"""
    from paper_analysis.services.qa_evaluation import CandidatePaper, QuestionCandidate

    rows = []
    for case in dataset.cases:
        paper = dataset.papers[case.paper_id]
        rows.append(QuestionCandidate(id=case.candidate_id, question=case.question,
            paper=CandidatePaper(source_path=paper.source_path, sha256=paper.sha256),
            figure=case.figure, panel=case.panel).model_dump_json())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _artifacts(run: EvaluationManifest, root: Path) -> dict[str, tuple[AnswerResponse, QuestionAudit, Path]]:
    artifacts = {}
    for record in run.results:
        if not record.answer_id:
            continue
        directory = root / "questions" / record.answer_id
        answer_path = directory / "answer.json"
        if not answer_path.is_file():
            continue
        answer = AnswerResponse.model_validate_json(answer_path.read_text())
        audit_path = directory / "job.json"
        from paper_analysis.domain.qa import QuestionJob
        job = QuestionJob.model_validate_json(audit_path.read_text())
        audit = QuestionAudit.model_validate_json((directory / f"audit-{job.attempt}.json").read_text())
        artifacts[record.candidate_id] = (answer, audit, answer_path)
    return artifacts


def create_review_template(dataset_path: Path, run_path: Path, output: Path) -> None:
    from paper_analysis.domain.evaluation import ClaimReview

    dataset = load_reference(dataset_path)
    run = EvaluationManifest.model_validate_json(run_path.read_text())
    artifacts = _artifacts(run, run_path.parent)
    cases = []
    for record in run.results:
        item = artifacts.get(record.candidate_id)
        answer, _, path = item if item else (None, None, None)
        cases.append(CaseReview(candidate_id=record.candidate_id,
            answer_id=str(answer.id) if answer else None, answer_sha256=file_sha256(path) if path else None,
            claim_reviews=[ClaimReview(answer_claim_id=c.claim_id, correctness="unverifiable", reason="待独立评价，模板不得直接作为已完成评价。")
                           for c in answer.claims] if answer else [],
            rationale="待独立阅读回答、原文与审计后填写。"))
    if {c.candidate_id for c in cases} - {c.candidate_id for c in dataset.cases}:
        raise ValueError("运行包含参考集之外的问题。")
    atomic_json(output, ReviewBundle(dataset_sha256=file_sha256(dataset_path), run_id=str(run.run_id),
        reviewer="待填写", review_kind="ai_assisted", cases=cases))


def _retrieved(case: ReferenceCase, audit: QuestionAudit) -> list[str]:
    evidence = [item for round_ in audit.rounds for item in round_.evidence]
    result = []
    for gold in case.gold_evidence:
        for item in evidence:
            if gold.source_kind == "vision":
                # 只表明实际图像输入可用；不表明 OCR 或视觉模型理解正确。
                matches = item.kind == "vision" and gold.pdf_page_1_based in {item.page, *item.image_pages} and item.figure == f"Figure {gold.figure}" and (not gold.panel or not item.panel or item.panel == gold.panel)
            else:
                matches = item.kind != "vision" and item.page == gold.pdf_page_1_based and normalize_quote(gold.verbatim_quote or "") in normalize_quote(item.excerpt)
            if matches:
                result.append(gold.evidence_id)
                break
    return result


def _score_case(case: ReferenceCase, execution: str, answer: AnswerResponse | None,
                audit: QuestionAudit | None, review: CaseReview | None) -> CaseScore:
    required = {c.claim_id for c in case.gold_claims if c.required}
    result = CaseScore(candidate_id=case.candidate_id, paper_id=case.paper_id, task_kind=case.task_kind,
        execution=execution, reviewed=review is not None, output_claims=len(answer.claims) if answer else 0,
        status_match=answer.status == case.expected_status if answer else None,
        retrieved_evidence_ids=_retrieved(case, audit) if audit else [])
    if review is None:
        return result
    if answer is None:
        if review.answer_id or review.claim_reviews:
            raise ValueError("无回答的运行不能绑定回答或主张评价。")
        result.complete, result.primary_error = False, "execution"
        result.missed_required_claim_ids = sorted(required)
        result.rationale = review.rationale
        return result
    actual = {c.claim_id for c in answer.claims}
    actual_claims = {c.claim_id: c for c in answer.claims}
    reviewed = {c.answer_claim_id for c in review.claim_reviews}
    if actual != reviewed:
        raise ValueError(f"{case.candidate_id}：必须逐条评价所有输出主张。")
    known = {c.claim_id for c in case.gold_claims}
    gold_claims = {c.claim_id: c for c in case.gold_claims}
    matched: set[str] = set()
    for item in review.claim_reviews:
        if item.citation_correct is None or (actual_claims[item.answer_claim_id].basis == "visual" and item.panel_aligned is None):
            raise ValueError("输出主张须评价引文；视觉主张还须评价图号/子图对齐。")
        if not set(item.matched_gold_claim_ids) <= known:
            raise ValueError("评价匹配未知参考主张。")
        if any(gold_claims[i].basis != actual_claims[item.answer_claim_id].basis for i in item.matched_gold_claim_ids):
            raise ValueError("正文主张不能冒充直接读图要求；主张依据类型必须与参考要求一致。")
        if item.correctness == "correct":
            result.correct_claims += 1
            matched.update(item.matched_gold_claim_ids)
        result.citation_correct += item.citation_correct is True
        result.citation_evaluated += item.citation_correct is not None
        result.panel_aligned += item.panel_aligned is True
        result.panel_evaluated += item.panel_aligned is not None
    result.matched_required_claim_ids = sorted(required & matched)
    result.missed_required_claim_ids = sorted(required - matched)
    judgments_complete = review.uncertainty_correct is not None and review.forbidden_inference_present is not None
    if not judgments_complete:
        raise ValueError(f"{case.candidate_id}：尚未评价不确定性或禁止推断。")
    result.complete = bool(result.status_match and not result.missed_required_claim_ids
        and result.correct_claims == len(answer.claims) and review.uncertainty_correct
        and not review.forbidden_inference_present
        and result.citation_correct == result.citation_evaluated
        and result.panel_aligned == result.panel_evaluated)
    if result.complete and (review.primary_error or review.secondary_errors):
        raise ValueError("完整正确题不能同时标为错误题。")
    result.primary_error = None if result.complete else review.primary_error or "unknown"
    result.secondary_errors = review.secondary_errors
    result.rationale = review.rationale
    return result


def _metrics(scores: list[CaseScore], cases: dict[str, ReferenceCase]) -> dict[str, ScoreRate]:
    reviewed = [s for s in scores if s.reviewed]
    required_total = sum(len([c for c in cases[s.candidate_id].gold_claims if c.required]) for s in reviewed)
    text_ids = {s.candidate_id: {e.evidence_id for e in cases[s.candidate_id].gold_evidence if e.source_kind != "vision"} for s in scores}
    visual_ids = {s.candidate_id: {e.evidence_id for e in cases[s.candidate_id].gold_evidence if e.source_kind == "vision"} for s in scores}
    answerable = [s for s in reviewed if cases[s.candidate_id].expected_status != "refused"]
    refusals = [s for s in reviewed if cases[s.candidate_id].expected_status == "refused"]
    return {
        "review_coverage": ScoreRate(numerator=len(reviewed), denominator=len(scores)),
        "claim_correctness": ScoreRate(numerator=sum(s.correct_claims for s in reviewed), denominator=sum(s.output_claims for s in reviewed)),
        "required_claim_recall": ScoreRate(numerator=sum(len(s.matched_required_claim_ids) for s in reviewed), denominator=required_total),
        "citation_correctness": ScoreRate(numerator=sum(s.citation_correct for s in reviewed), denominator=sum(s.citation_evaluated for s in reviewed)),
        "panel_alignment": ScoreRate(numerator=sum(s.panel_aligned for s in reviewed), denominator=sum(s.panel_evaluated for s in reviewed)),
        "status_match": ScoreRate(numerator=sum(s.status_match is True for s in reviewed), denominator=len(reviewed)),
        "complete_answerable": ScoreRate(numerator=sum(s.complete is True for s in answerable), denominator=len(answerable)),
        "correct_refusal": ScoreRate(numerator=sum(s.complete is True for s in refusals), denominator=len(refusals)),
        "text_evidence_recall": ScoreRate(numerator=sum(len(set(s.retrieved_evidence_ids) & text_ids[s.candidate_id]) for s in scores), denominator=sum(len(v) for v in text_ids.values())),
        "visual_input_coverage": ScoreRate(numerator=sum(len(set(s.retrieved_evidence_ids) & visual_ids[s.candidate_id]) for s in scores), denominator=sum(len(v) for v in visual_ids.values())),
    }


def score_run(dataset_path: Path, run_path: Path, *, review_path: Path | None = None) -> ScoreReport:
    dataset = load_reference(dataset_path)
    fingerprint = file_sha256(dataset_path)
    run = EvaluationManifest.model_validate_json(run_path.read_text())
    review = ReviewBundle.model_validate_json(review_path.read_text()) if review_path else None
    if review and (review.dataset_sha256 != fingerprint or review.run_id != str(run.run_id)):
        raise ValueError("评价与参考集或运行指纹不匹配。")
    if review and review.reviewer in {"", "待填写"}:
        raise ValueError("评价者尚未填写，模板不能作为完成评价。")
    case_map = {c.candidate_id: c for c in dataset.cases}
    records = {r.candidate_id: r for r in run.results}
    if len(records) != len(run.results) or not records.keys() <= case_map.keys():
        raise ValueError("运行的问题 ID 重复或不属于参考集。")
    if run.candidate_manifest_sha256 is None:
        raise ValueError("运行未记录候选清单指纹，无法进行绑定评分。")
    # 原问题必须来自参考集；禁止把 oracle 证据输入或其他问题误算成生产基线。
    from paper_analysis.services.qa_evaluation import CandidatePaper, QuestionCandidate
    expected_rows = [QuestionCandidate(id=c.candidate_id, question=c.question,
        paper=CandidatePaper(source_path=dataset.papers[c.paper_id].source_path, sha256=dataset.papers[c.paper_id].sha256),
        figure=c.figure, panel=c.panel).model_dump_json() for c in dataset.cases]
    expected_manifest = hashlib.sha256(("\n".join(expected_rows) + "\n").encode()).hexdigest()
    if run.candidate_manifest_sha256 != expected_manifest:
        raise ValueError("被测候选清单与参考问题不匹配。")
    reviews = {c.candidate_id: c for c in review.cases} if review else {}
    if not reviews.keys() <= records.keys():
        raise ValueError("评价包含未运行的问题。")
    artifacts = _artifacts(run, run_path.parent)
    scores = []
    for case in dataset.cases:
        record = records.get(case.candidate_id)
        item = artifacts.get(case.candidate_id)
        answer, audit, path = item if item else (None, None, None)
        paper = dataset.papers[case.paper_id]
        if answer and (answer.document_sha256 != paper.sha256 or str(answer.id) != record.answer_id
                       or answer.request.question != case.question or audit.document_sha256 != paper.sha256):
            raise ValueError("回答与被测论文或任务不匹配。")
        case_review = reviews.get(case.candidate_id)
        if case_review and answer and (case_review.answer_id != str(answer.id) or case_review.answer_sha256 != file_sha256(path)):
            raise ValueError("评价绑定的回答已改变，需重新评价。")
        scores.append(_score_case(case, record.execution if record else "not_run", answer, audit, case_review))
    errors = Counter(s.primary_error for s in scores if s.reviewed and s.complete is False)
    priorities = sorted(("retrieval", "vision", "answer"), key=lambda category: (-errors[category], ("retrieval", "vision", "answer").index(category)))
    return ScoreReport(dataset_id=dataset.dataset_id, dataset_sha256=fingerprint, run_id=str(run.run_id),
        reference_status=dataset.reference_status, review_kind=review.review_kind if review else None,
        metrics=_metrics(scores, case_map), by_task={kind: _metrics([s for s in scores if s.task_kind == kind], case_map) for kind in sorted({s.task_kind for s in scores})},
        error_counts=dict(errors), error_denominator=sum(errors.values()),
        optimization_priority=[p for p in priorities if errors[p]], cases=scores)


def save_score(report: ScoreReport, output: Path) -> None:
    atomic_json(output / "scores.json", report)
    labels = {"review_coverage": "独立评价覆盖", "claim_correctness": "输出主张正确率", "required_claim_recall": "必需主张召回", "citation_correctness": "引文正确率", "panel_alignment": "子图对齐", "status_match": "回答状态匹配", "complete_answerable": "可回答题完整通过", "correct_refusal": "不存在图号的正确拒答", "text_evidence_recall": "文本证据定位召回", "visual_input_coverage": "视觉证据输入覆盖"}
    lines = [f"# 固定样本评分：{report.dataset_id}", "", f"参考状态：`{report.reference_status}`；评价类型：`{report.review_kind or 'not_evaluated'}`。", "", "| 指标 | 分子/分母 | 比率 |", "|---|---:|---:|"]
    for name, rate in report.metrics.items():
        value = f"{rate.value:.1%}" if rate.value is not None else "未评价/不适用"
        lines.append(f"| {labels[name]} | {rate.numerator}/{rate.denominator} | {value} |")
    lines += ["", "## 主错误分类", "", "每道失败题只计一个主错误；次要错误保留在 JSON，比例分母为失败题数。", "", "| 分类 | 题数 | 失败题占比 |", "|---|---:|---:|"]
    for name, count in sorted(report.error_counts.items(), key=lambda pair: (-pair[1], pair[0])):
        lines.append(f"| {name} | {count} | {count / report.error_denominator:.1%} |")
    lines += ["", f"检索/读图/回答优化顺序：{' → '.join(report.optimization_priority) or '证据不足，尚不排序'}。", "", "## 逐题结果", "", "| 问题 | 完整通过 | 主错误 | 漏掉的必需主张 | 判定理由 |", "|---|---|---|---|---|"]
    for item in report.cases:
        reason = item.rationale.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {item.candidate_id} | {'是' if item.complete is True else '否' if item.complete is False else '未评价'} | {item.primary_error or '—'} | {', '.join(item.missed_required_claim_ids) or '—'} | {reason} |")
    lines += ["", "文本召回按同页原文定位片段匹配；视觉输入覆盖只说明目标页面证据可用。两者均不替代主张语义正确性。10 道不存在图号题单列，不能抬高 30 道可回答题的通过率。"]
    output.mkdir(parents=True, exist_ok=True)
    (output / "scores.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
