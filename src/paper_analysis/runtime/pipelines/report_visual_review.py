"""报告视觉结论使用同一直接看图复核；修改核验 verdict 后统一交付。"""
from pathlib import Path

from paper_analysis.domain.models import FactCheckBatch, FigureAnalysis, FigureEvidence
from paper_analysis.domain.qa import AnswerClaim, QuestionRequest
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.pipelines.claim_inventory import collect_claims
from paper_analysis.runtime.pipelines.visual_review import VisualReviewSession


def review_report_visuals(*, document: ParsedDocument, result: AnalysisResult,
                          analyses: list[FigureAnalysis], evidence: list[FigureEvidence],
                          checks: FactCheckBatch, session: VisualReviewSession | None,
                          ledger=None) -> None:
    visual_ids = {e.figure_id for e in evidence if e.semantic_source == "multimodal_llm"}
    claims = collect_claims(analysis_result=result, figure_analyses=analyses)
    reports = []
    reviewed = []
    for figure in document.figures:
        if figure.figure_id not in visual_ids:
            continue
        selected = [c for c in claims if figure.figure_id in c.evidence_ids]
        if not selected:
            continue
        accepted = set()
        if session:
            paths = [Path(p) for p in [figure.page_snapshot_path, *figure.context_page_snapshot_paths] if p]
            if not paths:
                paths = [Path(p) for p in figure.image_block_paths]
            review = session.review(request=QuestionRequest(question="逐条核对报告图像结论，不推断不可见细节。"),
                claims=[AnswerClaim(**c.model_dump(), basis="visual") for c in selected],
                image_paths=paths[:4], execution_context=ledger)
            reports.append({"figure_id": figure.figure_id, **review.model_dump(mode="json")})
            accepted = {c.claim_id for c in review.checks if c.verdict == "supported"} if review.status == "reviewed" else set()
            if accepted:
                reviewed.append(figure.figure_id)
        for check in checks.checks:
            if check.claim_id in {c.claim_id for c in selected} and check.claim_id not in accepted:
                check.verdict = "unverifiable"
                check.rationale = "直接看图复核未支持该报告主张。"
    result.structured_data["report_visual_reviews"] = reports
    result.structured_data["visually_reviewed_figures"] = reviewed
