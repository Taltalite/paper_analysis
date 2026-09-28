"""有界文内检索 → CrewAI 问答 → 既有事实核验及 QC，不调用全文报告。"""
from __future__ import annotations

import re
import time
from collections.abc import Callable

from paper_analysis.adapters.parser.figure_semantics_base import FigureSemanticExtractor
from paper_analysis.domain.models import DocumentBlock
from paper_analysis.domain.qa import AnswerDraft, AnswerResponse, EvidenceLocation, QuestionRequest, QuestionRound
from paper_analysis.domain.quality import QualityReport
from paper_analysis.runtime.pipelines.qa_quality import enforce_qa_evidence
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.crews.research.fact_check import FactCheckRunner
from paper_analysis.runtime.crews.research.question_answer import QuestionAnswerRunner
from paper_analysis.runtime.pipelines.quality_control import apply_quality_gate


def figure_number(value: str) -> str:
    return re.sub(r"^(?:figure|fig\.?|图)\s*", "", value.strip(), flags=re.I).upper()


class QuestionAnswerPipeline:
    def __init__(self, *, runner: QuestionAnswerRunner, checker: FactCheckRunner,
                 vision: FigureSemanticExtractor) -> None:
        self.runner, self.checker, self.vision = runner, checker, vision

    def run(self, *, document: ParsedDocument, request: QuestionRequest,
            audit_sink: Callable[[QuestionRound], None] | None = None) -> AnswerResponse:
        if request.panel:
            request = request.model_copy(update={"panel": request.panel.lower()})
        blocks = [DocumentBlock.model_validate(b) for b in document.metadata.get("ordered_blocks", [])]
        caption_owners = {bid: f.figure_id for f in document.figures for bid in f.caption_block_ids}
        target = figure_number(request.figure) if request.figure else None
        match = re.search(r"(?:figure|fig\.?|图)\s*([Ss]?\d+)([a-z])?", request.question, re.I)
        if match:
            if target is None:
                target = match[1].upper()
            if target == match[1].upper():
                request = request.model_copy(update={"figure": target, "panel": request.panel or match[2]})
        if target is None and any(word in request.question.lower() for word in ("图", "figure", "panel", "坐标", "曲线")):
            terms = self._terms(request.question)
            ranked_figures = sorted(document.figures,
                key=lambda f: sum(t in f.caption.lower() for t in terms), reverse=True)
            scores = [sum(t in f.caption.lower() for t in terms) for f in ranked_figures]
            if len(scores) > 1 and (scores[0] == 0 or scores[0] == scores[1]):
                return AnswerResponse(request=request, status="refused", answer="无法唯一确定所问图表，请指定图号或子图。",
                    uncertainties=["图注关键词不足以确定目标图，不自动选择其他图替代。"],
                    quality=QualityReport(status="blocked"), stop_reason="target_unresolved")
            if ranked_figures:
                target = figure_number(ranked_figures[0].figure_id)
                request = request.model_copy(update={"figure": target})
            else:
                return AnswerResponse(request=request, status="refused", answer="未识别到可定位的图表，暂不能回答该图表问题。",
                    uncertainties=["解析器未提供图表定位。"], visual_status="failed", quality=QualityReport(status="blocked"), stop_reason="target_unresolved")
        figures = [f for f in document.figures if target and figure_number(f.figure_id) == target]
        warnings: list[str] = []
        if target and not figures:
            return AnswerResponse(request=request, status="refused", answer="未在解析结果中找到指定图号，无法可靠回答。",
                uncertainties=["请核对图号；当前解析器可能未识别补充图或扫描图注。"],
                visual_status="failed", quality=QualityReport(status="blocked"), stop_reason="target_unresolved")
        selected: dict[str, EvidenceLocation] = {}
        for figure in figures:
            if figure.page_number and figure.caption:
                selected[figure.figure_id] = EvidenceLocation(evidence_id=figure.figure_id, kind="caption",
                    page=figure.page_number, figure=figure.figure_id, excerpt=figure.caption[:4000])
        visual_status = "not_requested"
        if target:
            visual_status = "failed"
            for figure in figures[:1]:
                try:
                    artifacts = self.vision.extract(document=document, figures=[figure]).artifacts
                except Exception:
                    artifacts = []
                for artifact in artifacts:
                    if artifact.figure_id != figure.figure_id or artifact.extraction_source != "multimodal_llm":
                        continue
                    warnings.extend(artifact.uncertainties)
                    content = artifact.direct_evidence
                    confidence = artifact.confidence
                    if request.panel:
                        panels = [p for p in artifact.panels if p.panel_label.lower() == request.panel.lower()]
                        content = [p.summary for p in panels] + [t for p in panels for t in p.visible_text]
                        confidence = panels[0].confidence if len(panels) == 1 else "不足以判断"
                    if not content or confidence not in {"高", "中"} or not figure.page_number:
                        continue
                    identifier = f"vision:{figure.figure_id}:{request.panel or 'all'}"
                    # 定位为实际送入适配器的页面集合，不猜测图形一定在图注所在页。
                    pages = sorted({int(m[1]) for path in artifact.image_block_paths
                                    if (m := re.search(r"page_(\d+)\.png$", path))})
                    allowed_pages = {figure.page_number, *[int(m[1]) for path in figure.context_page_snapshot_paths
                        if (m := re.search(r"page_(\d+)\.png$", path))]}
                    if not pages or not set(pages) <= allowed_pages:
                        continue
                    selected[identifier] = EvidenceLocation(evidence_id=identifier, kind="vision",
                        page=figure.page_number, figure=figure.figure_id, panel=request.panel,
                        excerpt="\n".join(content)[:4000], image_pages=pages)
                    visual_status = "succeeded"
            if visual_status == "failed":
                warnings.append("目标图或子图未获得可用真实页面视觉证据；仅可引用正文或图注，不能声称读图成功。")
        terms = self._terms(request.question)
        feedback: list[str] = []
        draft = AnswerDraft()
        result = AnalysisResult()
        quality = QualityReport(status="blocked")
        accepted = []
        round_index = 0
        best: tuple | None = None
        stop_reason = "budget_exhausted"
        gaps: list[str] = []
        previous_signature: str | None = None
        for round_index in range(request.max_followups + 1):
            started = time.monotonic()
            previous_ids = set(selected)
            gap_words = {"methods": "method protocol preparation", "controls": "control wild type untreated",
                         "statistics": "replicate statistical test p-value standard deviation", "results": "result difference"}
            terms.update(self._terms(" ".join(gap_words[g] for g in gaps)))
            # 每轮最多新增四块，累计文本不超过 18,000 字符；不向模型重复发送全文。
            reference_ids = {bid for f in figures for bid in f.reference_block_ids}
            ranked = sorted((b for b in blocks if b.text and b.page_number > 0 and b.block_id not in selected),
                key=lambda b: (b.block_id in reference_ids, sum(t in b.text.lower() for t in terms)), reverse=True)
            for block in ranked[:4]:
                remaining = 18000 - sum(len(e.excerpt) for e in selected.values())
                if remaining <= 0:
                    break
                owner = caption_owners.get(block.block_id)
                selected[block.block_id] = EvidenceLocation(evidence_id=block.block_id, kind="caption" if owner else "text",
                    figure=owner,
                    page=block.page_number, block_id=block.block_id, bbox=block.bbox, excerpt=block.text[:min(1500, remaining)])
            new_ids = sorted(set(selected) - previous_ids)
            if round_index and not new_ids and not feedback:
                stop_reason = "no_new_evidence"
                round_index -= 1
                break
            if not selected:
                stop_reason = "no_locatable_evidence"
                warnings.append("没有可定位的正文或图表证据。")
                break
            evidence = list(selected.values())
            audit_round = QuestionRound(index=round_index, evidence=evidence, new_evidence_ids=new_ids)
            try:
                draft = self.runner.run(request=request, evidence=evidence, feedback=[*warnings, *feedback])
                audit_round.draft = draft
                # 使用独立的、仅含已选证据的 ParsedDocument 视图复用既有核验与 QC。
                view = ParsedDocument(title=document.title,
                    sections={"results": "\n".join(f"[{e.evidence_id}] ({e.kind}) {e.excerpt}" for e in evidence)},
                    raw_text="\n".join(e.excerpt for e in evidence),
                    metadata={"qa_bounded_evidence": True,
                              "ordered_blocks": [{"block_id": e.evidence_id, "text": e.excerpt} for e in evidence]})
                result = AnalysisResult(structured_data={"claims": [c.model_dump() for c in draft.claims]})
                checks = self.checker.run(document=view, analysis_result=result, figure_analyses=[], figure_evidence=[])
                audit_round.checks = checks
                apply_quality_gate(document=view, result=result, figure_analyses=[], figure_evidence=[], fact_checks=checks)
                quality = result.quality or quality
                enforce_qa_evidence(draft=draft, evidence=selected, request=request, quality=quality)
                audit_round.draft, audit_round.checks, audit_round.quality = draft, checks, quality
                accepted = [c for c in draft.claims if c.claim_id in quality.accepted_claim_ids]
            except Exception:
                warnings.append("问答生成或事实核验失败，本轮未获核验的内容不予交付。")
                audit_round.error = "生成或核验失败（详情不包含供应商敏感响应）。"
                stop_reason = "model_error"
                accepted = []
                quality = QualityReport(status="blocked")
                break
            finally:
                audit_round.elapsed_seconds = round(time.monotonic() - started, 3)
                if audit_sink:
                    audit_sink(audit_round)
            if accepted and (best is None or len(accepted) >= len(best[0])):
                best = (accepted, quality, draft)

            feedback = [i.message for i in quality.issues]
            gaps = draft.evidence_gaps
            signature = draft.model_dump_json() + str(quality.accepted_claim_ids)
            if round_index and not new_ids and signature == previous_signature:
                stop_reason = "no_new_evidence"
                break
            previous_signature = signature
            if draft.sufficient and len(accepted) == len(draft.claims) and accepted:
                stop_reason = "completed"
                break
            terms.update(self._terms(" ".join(draft.search_terms)))
        if best is not None and stop_reason == "model_error":
            accepted, quality, draft = best
            warnings.append("后续调用失败，保留此前已核验的部分回答；新增证据尚未完成核验。")
        complete = bool(accepted) and draft.sufficient and len(accepted) == len(draft.claims) and not warnings
        status = "answered" if complete else ("partial" if accepted else "refused")
        uncertainties = list(dict.fromkeys([*warnings, *draft.uncertainties, *feedback]))
        if status != "answered":
            uncertainties.append("当前证据或核验不足以完整回答问题。")
        used = {eid for claim in accepted for eid in claim.evidence_ids}
        # 同时返回实际核验所用的证据集合，保留正文/图注/视觉来源区分。
        return AnswerResponse(request=request, status=status,
            answer="\n".join(c.statement for c in accepted) or "证据不足，暂不能可靠回答该问题。",
            claims=accepted, evidence=[e for e in selected.values() if e.evidence_id in used],
            uncertainties=uncertainties, visual_status=visual_status, followups=round_index, quality=quality, stop_reason=stop_reason)

    @staticmethod
    def _terms(text: str) -> set[str]:
        terms = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+", text.lower()))
        expansions = {"甲基化": "methylation", "可及性": "atac accessibility", "组蛋白": "histone",
                      "对照": "control", "重复": "replicate", "显著": "significant p-value",
                      "表达": "expression", "染色质": "chromatin", "差异": "differential"}
        for key, value in expansions.items():
            if key in text:
                terms.update(value.split())
        return terms
