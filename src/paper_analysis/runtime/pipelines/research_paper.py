from __future__ import annotations

from paper_analysis.domain.execution_context import scoped_execution

import asyncio
import re

from pydantic import ValidationError

from paper_analysis.domain.models import (
    DocumentStructureDraft,
    FactCheckBatch,
    FigureAnalysis,
    FigureAnalysisBatch,
    FigureEvidence,
    FigureEvidenceBatch,
    FigureMetadata,
    FigureSemanticArtifact,
    FigureSemanticArtifactBatch,
)
from paper_analysis.domain.execution import ResolvedPolicy
from paper_analysis.domain.execution import CallStatus
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.crews.base import TextAnalysisCrewRunner
from paper_analysis.runtime.crews.research import (
    DocumentStructuringRunner,
    FactCheckRunner,
    FigureAnalysisRunner,
    FigureEvidenceCuratorRunner,
    FigureGroundingRunner,
)
from paper_analysis.runtime.pipelines.general_text import GeneralTextPipeline
from paper_analysis.runtime.pipelines.base import AnalysisPipeline
from paper_analysis.runtime.pipelines.profiles import RESEARCH_PAPER_PROFILE
from paper_analysis.runtime.pipelines.research_paper_report import ResearchPaperReportRenderer
from paper_analysis.runtime.budget import BudgetLedger, estimate_text_tokens


class ResearchPaperPipeline(AnalysisPipeline):
    def __init__(
        self,
        *,
        crew_runner: TextAnalysisCrewRunner | None = None,
        structuring_runner: DocumentStructuringRunner | None = None,
        figure_grounding_runner: FigureGroundingRunner | None = None,
        figure_evidence_curator: FigureEvidenceCuratorRunner | None = None,
        figure_runner: FigureAnalysisRunner | None = None,
        fact_check_runner: FactCheckRunner | None = None,
        report_renderer: ResearchPaperReportRenderer | None = None,
        parallel_stages: bool = False,
        visual_checker=None,
    ) -> None:
        self._pipeline = GeneralTextPipeline(
            profile=RESEARCH_PAPER_PROFILE,
            crew_runner=crew_runner,
        )
        self._structuring_runner = structuring_runner
        self._figure_grounding_runner = figure_grounding_runner
        self._figure_evidence_curator = figure_evidence_curator
        self._figure_runner = figure_runner
        self._fact_check_runner = fact_check_runner
        self._report_renderer = report_renderer or ResearchPaperReportRenderer()
        self._parallel_stages = parallel_stages
        self._visual_checker = visual_checker

    @scoped_execution
    async def run(
        self,
        document: ParsedDocument,
        policy: ResolvedPolicy | None = None,
        execution_context: BudgetLedger | None = None,
    ) -> AnalysisResult:
        resolved = policy or ResolvedPolicy.resolve()
        if execution_context and getattr(self._pipeline._crew_runner, "request_metering", False):
            execution_context.verification_reserve = min(resolved.effective.max_output_tokens * 2, resolved.effective.token_budget // 4)
        source_document = self._refine_document_structure(document, execution_context=execution_context)
        focused_document, selected_sections = self._build_focus_document(source_document)
        if self._parallel_stages:
            result, figure_outputs = await asyncio.gather(
                self._pipeline.arun(focused_document, policy=resolved, execution_context=execution_context),
                self._run_figure_pipeline_async(
                    source_document=source_document,
                    selected_sections=selected_sections,
                    max_figures=resolved.effective.max_figures,
                    execution_context=execution_context,
                ),
            )
            semantic_artifacts, figure_evidence, figure_analyses = figure_outputs
        else:
            result = await self._pipeline.run(
                focused_document, policy=resolved, execution_context=execution_context
            )
            semantic_artifacts, figure_evidence, figure_analyses = self._run_figure_pipeline(
                source_document=source_document,
                selected_sections=selected_sections,
                max_figures=resolved.effective.max_figures,
                execution_context=execution_context,
            )
        fact_checks = self._run_fact_checks(
            source_document=source_document,
            result=result,
            figure_evidence=figure_evidence,
            figure_analyses=figure_analyses,
            execution_context=execution_context,
        )
        from paper_analysis.runtime.pipelines.quality_control import apply_quality_gate
        from paper_analysis.runtime.pipelines.visual_review import VisualReviewSession
        from paper_analysis.runtime.pipelines.report_visual_review import review_report_visuals
        session = VisualReviewSession(self._visual_checker, max_calls=resolved.effective.max_visual_reviews) if self._visual_checker else None
        attempts = []
        loop_stop = "completed"
        # 默认保持单遍；显式 report_followups 才启用有界定向修复。
        for index in range(resolved.effective.report_followups + 1):
            review_report_visuals(document=source_document, result=result, analyses=figure_analyses,
                evidence=figure_evidence, checks=fact_checks, session=session, ledger=execution_context)
            checked = result.model_copy(deep=True)
            apply_quality_gate(document=source_document, result=checked, figure_analyses=figure_analyses,
                figure_evidence=figure_evidence, fact_checks=fact_checks)
            attempts.append({"index": index, "accepted": list(checked.quality.accepted_claim_ids),
                             "issues": [issue.code for issue in checked.quality.issues]})
            if not checked.quality.issues:
                break
            if index >= resolved.effective.report_followups:
                loop_stop = "round_limit"
                break
            remaining = [name for name in source_document.section_order if name not in selected_sections and source_document.sections.get(name)]
            if not remaining:
                loop_stop = "no_new_evidence"
                break
            section = remaining[0]
            repair_document = focused_document.model_copy(deep=True)
            repair_document.raw_text = focused_document.raw_text[:6000] + "\n补取章节：\n" + source_document.sections[section][:5000]
            repair_document.metadata["repair_feedback"] = [i.code for i in checked.quality.issues]
            try:
                candidate = await self._pipeline.run(repair_document, policy=resolved, execution_context=execution_context)
                revised = self._run_fact_checks(source_document=source_document, result=candidate,
                    figure_evidence=figure_evidence, figure_analyses=figure_analyses, execution_context=execution_context)
                if execution_context and execution_context.stop_reason:
                    loop_stop = execution_context.stop_reason.value
                    break
                result, fact_checks = candidate, revised
                selected_sections.append(section)
            except Exception:
                loop_stop = "provider_error"
                break  # 保留最近已核验结果；新的未核验候选不得替代正式产物。
        result.structured_data["report_rounds"] = attempts
        result.structured_data["execution_stop_reason"] = loop_stop
        result.structured_data = self._merge_parser_metadata(
            structured_data=result.structured_data,
            source_document=source_document,
        )
        result.structured_data = {
            **result.structured_data,
            "semantic_artifacts": [artifact.model_dump() for artifact in semantic_artifacts],
            "figure_evidence": [evidence.model_dump() for evidence in figure_evidence],
            "figure_analyses": [analysis.model_dump() for analysis in figure_analyses],
            "fact_checks": [check.model_dump() for check in fact_checks.checks],
            "fact_check_summary": fact_checks.overall_assessment,
            "fact_check_rule_flags": fact_checks.rule_flags,
            "selected_sections": selected_sections,
            "source_structure": {
                "parser_kind": source_document.metadata.get("parser_kind", "unknown"),
                "page_count": source_document.metadata.get("page_count"),
                "doi": source_document.metadata.get("doi", ""),
                "section_order": source_document.section_order,
                "figure_count": len(source_document.figures),
            },
        }
        result.markdown_report = self._report_renderer.render(
            source_document=source_document,
            result=result,
            selected_sections=selected_sections,
            figure_evidence=figure_evidence,
            figure_analyses=figure_analyses,
            fact_checks=fact_checks,
        )
        result.policy = resolved
        return result

    @staticmethod
    def _build_focus_document(document: ParsedDocument) -> tuple[ParsedDocument, list[str]]:
        priority = [
            "abstract",
            "introduction",
            "method",
            "experimental_setup",
            "results",
            "conclusion",
            "figures",
        ]
        selected_sections = [name for name in priority if document.sections.get(name)]
        if not selected_sections:
            selected_sections = [name for name in document.section_order if document.sections.get(name)]

        # 优先为方法、结果和实验保留空间，避免长引言挤掉关键证据。
        caps = {"abstract": 1000, "introduction": 800, "method": 2800,
                "experimental_setup": 2000, "results": 3600, "conclusion": 800, "figures": 500}
        chunks: list[str] = []
        total_chars = 0
        included: list[str] = []
        for section_name in selected_sections:
            content = document.sections.get(section_name, "").strip()
            if not content:
                continue
            heading = f"## {section_name.replace('_', ' ').title()}\n"
            separator = 2 if chunks else 0
            remaining = 12000 - total_chars - separator - len(heading)
            if remaining <= 0:
                break
            excerpt = content[:min(remaining, caps.get(section_name, 2000))]
            chunk = heading + excerpt
            chunks.append(chunk)
            included.append(section_name)
            total_chars += len(chunk) + separator

        focus_text = "\n\n".join(chunks).strip() or document.raw_text[:12000]
        selected_sections = included
        focused_document = ParsedDocument(
            title=document.title,
            raw_text=focus_text,
            markdown=document.markdown,
            sections=document.sections,
            section_order=document.section_order,
            figures=document.figures,
            metadata={**document.metadata, "selected_sections": selected_sections},
        )
        return focused_document, selected_sections

    def _refine_document_structure(
        self,
        document: ParsedDocument,
        *,
        execution_context: BudgetLedger | None = None,
    ) -> ParsedDocument:
        if document.metadata.get("parser_kind") != "pdf":
            return document

        draft = self._coarse_structure_draft(document)
        if self._structuring_runner is not None and self._needs_structure_refinement(document):
            reservation = None
            if execution_context is not None:
                reservation = self._reserve_stage(
                    execution_context,
                    text=document.raw_text[:24_000],
                    stage="document_structuring",
                    role="document_structuring",
                )
                execution_context.mark_sent(reservation)
            try:
                draft = self._structuring_runner.run(document=document)
            except Exception:
                if reservation is not None:
                    execution_context.settle(reservation, usage=None, status=CallStatus.PROVIDER_ERROR)
                raise
            if reservation is not None:
                execution_context.settle(reservation, usage=None)
        draft.figures = self._restore_figure_assets(document.figures, draft.figures)

        title = draft.title or document.title
        merged_metadata = {
            **document.metadata,
            "qc_original_sections": document.metadata.get("qc_original_sections", dict(document.sections)),
            "title": title,
            "authors": draft.authors or document.metadata.get("authors", []),
            "doi": draft.doi or document.metadata.get("doi", ""),
            "venue": draft.venue or document.metadata.get("venue", ""),
            "year": draft.year or document.metadata.get("year", ""),
            "coarse_structure": draft.model_dump(mode="json"),
        }
        sections = self._sections_from_draft(draft=draft, original_sections=document.sections, title=title)
        raw_text = "\n\n".join(
            content for key, content in sections.items() if key not in {"title", "figures"} and content
        ).strip() or document.raw_text
        return ParsedDocument(
            title=title,
            raw_text=raw_text,
            markdown=document.markdown,
            sections=sections,
            section_order=list(sections.keys()),
            figures=draft.figures or document.figures,
            metadata=merged_metadata,
        )

    def _reserve_stage(
        self,
        execution_context: BudgetLedger,
        *,
        text: str,
        stage: str,
        role: str,
    ):
        runner = {"document_structuring": self._structuring_runner, "figure_analysis": self._figure_runner,
                  "fact_check": self._fact_check_runner}.get(stage)
        if getattr(runner, "request_metering", False):
            return None
        return execution_context.reserve(
            input_tokens=estimate_text_tokens(text[:24_000]),
            stage=stage,
            role=role,
            model="configured-text-model",
            endpoint_id="crewai:text",
        )

    @staticmethod
    def _restore_figure_assets(
        originals: list[FigureMetadata], refined: list[FigureMetadata],
    ) -> list[FigureMetadata]:
        """结构修复只能更新文字；本地资产路径必须来自 parser，且不能丢失原图。"""
        def key(figure: FigureMetadata) -> str:
            return re.sub(r"^fig(?:ure)?\.?\s*", "figure", figure.figure_id.lower()).strip()

        originals_by_id = {key(figure): figure for figure in originals}
        merged: list[FigureMetadata] = []
        seen: set[str] = set()
        for figure in refined:
            identifier = key(figure)
            if identifier in seen:
                continue
            seen.add(identifier)
            original = originals_by_id.get(identifier)
            merged.append(figure.model_copy(update={
                "figure_id": original.figure_id if original else figure.figure_id,
                "page_number": original.page_number if original else figure.page_number,
                "page_snapshot_path": original.page_snapshot_path if original else None,
                "context_page_snapshot_paths": original.context_page_snapshot_paths if original else [],
                "image_block_paths": original.image_block_paths if original else [],
                "caption_block_ids": original.caption_block_ids if original else [],
                "reference_block_ids": original.reference_block_ids if original else [],
            }))
        merged.extend(figure for figure in originals if key(figure) not in seen)
        return merged

    def _run_figure_pipeline(
        self,
        *,
        source_document: ParsedDocument,
        selected_sections: list[str],
        max_figures: int = 4,
        execution_context: BudgetLedger | None = None,
    ) -> tuple[list[FigureSemanticArtifact], list[FigureEvidence], list[FigureAnalysis]]:
        if not source_document.figures:
            return [], [], []

        selected_figures = self._select_figures_for_analysis(
            document=source_document,
            selected_sections=selected_sections,
            max_figures=max_figures,
        )
        if not selected_figures:
            return [], [], []

        semantic_batch = self._run_figure_grounding(
            source_document=source_document,
            selected_figures=selected_figures,
            execution_context=execution_context,
        )
        evidence_batch = self._run_figure_evidence_curator(
            source_document=source_document,
            selected_figures=selected_figures,
            semantic_batch=semantic_batch,
        )
        analysis_batch = self._run_figure_analysis(
            source_document=source_document,
            evidence_batch=evidence_batch,
            execution_context=execution_context,
        )
        return semantic_batch.artifacts, evidence_batch.evidences, analysis_batch.analyses

    async def _run_figure_pipeline_async(
        self,
        *,
        source_document: ParsedDocument,
        selected_sections: list[str],
        max_figures: int = 4,
        execution_context: BudgetLedger | None = None,
    ) -> tuple[list[FigureSemanticArtifact], list[FigureEvidence], list[FigureAnalysis]]:
        """并行模式下的图表阶段：grounding/curator 为确定性或 adapter 调用，保持同步；
        仅 LLM 图表分析阶段走原生异步，与正文理解并行。"""
        if not source_document.figures:
            return [], [], []

        selected_figures = self._select_figures_for_analysis(
            document=source_document,
            selected_sections=selected_sections,
            max_figures=max_figures,
        )
        if not selected_figures:
            return [], [], []

        semantic_batch = self._run_figure_grounding(
            source_document=source_document,
            selected_figures=selected_figures,
            execution_context=execution_context,
        )
        evidence_batch = self._run_figure_evidence_curator(
            source_document=source_document,
            selected_figures=selected_figures,
            semantic_batch=semantic_batch,
        )
        analysis_batch = await self._run_figure_analysis_async(
            source_document=source_document,
            evidence_batch=evidence_batch,
            execution_context=execution_context,
        )
        return semantic_batch.artifacts, evidence_batch.evidences, analysis_batch.analyses

    async def _run_figure_analysis_async(
        self,
        *,
        source_document: ParsedDocument,
        evidence_batch: FigureEvidenceBatch,
        execution_context: BudgetLedger | None = None,
    ) -> FigureAnalysisBatch:
        if self._figure_runner is None or not evidence_batch.evidences:
            return FigureAnalysisBatch()
        arun = getattr(self._figure_runner, "arun", None)
        if execution_context is None:
            if callable(arun):
                batch = await arun(document=source_document, figure_evidences=evidence_batch)
            else:
                batch = self._figure_runner.run(
                    document=source_document,
                    figure_evidences=evidence_batch,
                )
        else:
            reservation = self._reserve_stage(
                execution_context,
                text=str(evidence_batch.model_dump(mode="json")),
                stage="figure_analysis",
                role="figure_understanding",
            )
            execution_context.mark_sent(reservation)
            try:
                if callable(arun):
                    batch = await arun(document=source_document, figure_evidences=evidence_batch)
                else:
                    batch = self._figure_runner.run(
                        document=source_document,
                        figure_evidences=evidence_batch,
                    )
            except Exception:
                execution_context.settle(reservation, usage=None, status=CallStatus.PROVIDER_ERROR)
                raise
            execution_context.settle(reservation, usage=None)
        if isinstance(batch, FigureAnalysisBatch):
            return batch
        return FigureAnalysisBatch()

    def _run_figure_grounding(
        self,
        *,
        source_document: ParsedDocument,
        selected_figures: list[FigureMetadata],
        execution_context: BudgetLedger | None = None,
    ) -> FigureSemanticArtifactBatch:
        if self._figure_grounding_runner is None:
            return FigureSemanticArtifactBatch()
        if execution_context is None:
            batch = self._figure_grounding_runner.run(
                document=source_document,
                figures=selected_figures,
            )
        else:
            try:
                batch = self._figure_grounding_runner.run(
                    document=source_document,
                    figures=selected_figures,
                    execution_context=execution_context,
                )
            except TypeError:
                batch = self._figure_grounding_runner.run(
                    document=source_document,
                    figures=selected_figures,
                )
        if isinstance(batch, FigureSemanticArtifactBatch):
            return batch
        return FigureSemanticArtifactBatch()

    def _run_figure_evidence_curator(
        self,
        *,
        source_document: ParsedDocument,
        selected_figures: list[FigureMetadata],
        semantic_batch: FigureSemanticArtifactBatch,
    ) -> FigureEvidenceBatch:
        if self._figure_evidence_curator is None:
            return FigureEvidenceBatch()
        batch = self._figure_evidence_curator.run(
            document=source_document,
            figures=selected_figures,
            semantic_artifacts=semantic_batch,
        )
        if isinstance(batch, FigureEvidenceBatch):
            return batch
        return FigureEvidenceBatch()

    def _run_figure_analysis(
        self,
        *,
        source_document: ParsedDocument,
        evidence_batch: FigureEvidenceBatch,
        execution_context: BudgetLedger | None = None,
    ) -> FigureAnalysisBatch:
        if self._figure_runner is None or not evidence_batch.evidences:
            return FigureAnalysisBatch()
        reservation = None
        if execution_context is not None:
            reservation = self._reserve_stage(
                execution_context,
                text=str(evidence_batch.model_dump(mode="json")),
                stage="figure_analysis",
                role="figure_understanding",
            )
            execution_context.mark_sent(reservation)
        try:
            batch = self._figure_runner.run(
                document=source_document,
                figure_evidences=evidence_batch,
            )
        except Exception:
            if reservation is not None:
                execution_context.settle(reservation, usage=None, status=CallStatus.PROVIDER_ERROR)
            raise
        if reservation is not None:
            execution_context.settle(reservation, usage=None)
        if isinstance(batch, FigureAnalysisBatch):
            return batch
        return FigureAnalysisBatch()

    def _run_fact_checks(
        self,
        *,
        source_document: ParsedDocument,
        result: AnalysisResult,
        figure_evidence: list[FigureEvidence],
        figure_analyses: list[FigureAnalysis],
        execution_context: BudgetLedger | None = None,
    ) -> FactCheckBatch:
        if self._fact_check_runner is None:
            return FactCheckBatch(overall_assessment="未配置事实检查 agent。")
        reservation = None
        if execution_context is not None:
            reservation = self._reserve_stage(
                execution_context,
                text=source_document.raw_text[:24_000] + str(result.structured_data),
                stage="fact_check",
                role="fact_checker",
            )
            execution_context.mark_sent(reservation)
        try:
            batch = self._fact_check_runner.run(
                document=source_document,
                analysis_result=result,
                figure_analyses=figure_analyses,
                figure_evidence=figure_evidence,
            )
        except Exception:
            if reservation is not None:
                execution_context.settle(reservation, usage=None, status=CallStatus.PROVIDER_ERROR)
            raise
        if reservation is not None:
            execution_context.settle(reservation, usage=None)
        if isinstance(batch, FactCheckBatch):
            return batch
        return FactCheckBatch(overall_assessment="事实检查 agent 未返回有效结果。")

    @staticmethod
    def _needs_structure_refinement(document: ParsedDocument) -> bool:
        if document.metadata.get("structure_needs_refinement") is True:
            return True
        if not document.title.strip():
            return True
        if not document.sections.get("abstract"):
            return True
        has_core_section = any(
            document.sections.get(name)
            for name in ("method", "experimental_setup", "results", "conclusion")
        )
        if not has_core_section:
            return True
        return any(not figure.caption.strip() for figure in document.figures)

    @staticmethod
    def _coarse_structure_draft(document: ParsedDocument) -> DocumentStructureDraft:
        payload = document.metadata.get("coarse_structure")
        if isinstance(payload, dict):
            try:
                return DocumentStructureDraft.model_validate(payload)
            except ValidationError:
                pass
        return DocumentStructureDraft(
            title=document.title,
            sections=document.sections,
            section_order=document.section_order,
            figures=document.figures,
        )

    @staticmethod
    def _merge_parser_metadata(
        *,
        structured_data: dict[str, object],
        source_document: ParsedDocument,
    ) -> dict[str, object]:
        metadata = structured_data.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        parser_authors = source_document.metadata.get("authors", [])
        authors_value = metadata.get("authors")
        if not authors_value and parser_authors:
            metadata["authors"] = parser_authors
        if not metadata.get("title") and source_document.title:
            metadata["title"] = source_document.title
        if not metadata.get("venue") and source_document.metadata.get("venue"):
            metadata["venue"] = source_document.metadata.get("venue")
        if not metadata.get("year") and source_document.metadata.get("year"):
            metadata["year"] = source_document.metadata.get("year")

        return {
            **structured_data,
            "metadata": metadata,
        }

    @staticmethod
    def _select_figures_for_analysis(
        *,
        document: ParsedDocument,
        selected_sections: list[str],
        max_figures: int = 4,
    ) -> list[FigureMetadata]:
        if not document.figures:
            return []

        context_text = "\n".join(
            document.sections.get(section, "")
            for section in selected_sections
            if section in {"experimental_setup", "results", "conclusion", "figures"}
        )
        scored_figures: list[tuple[int, FigureMetadata]] = []
        for figure in document.figures:
            score = 0
            if figure.figure_id and figure.figure_id.lower() in context_text.lower():
                score += 2
            if figure.referenced_text_spans:
                score += 2
            if re.search(r"(result|increase|accuracy|compare|improvement|performance)", figure.caption, re.IGNORECASE):
                score += 1
            scored_figures.append((score, figure))

        ranked = [figure for _, figure in sorted(scored_figures, key=lambda item: item[0], reverse=True)]
        return ranked[:max(0, max_figures)]

    @staticmethod
    def _sections_from_draft(
        *,
        draft: DocumentStructureDraft,
        original_sections: dict[str, str],
        title: str,
    ) -> dict[str, str]:
        sections = {"title": title} if title else {}
        for key in draft.section_order:
            value = draft.sections.get(key, "")
            if value:
                sections[key] = value
        for key, value in draft.sections.items():
            if key not in sections and value:
                sections[key] = value
        for key, value in original_sections.items():
            if key not in sections and value:
                sections[key] = value
        if draft.figures:
            sections["figures"] = "\n\n".join(
                "\n".join(
                    [
                        f"### {figure.figure_id or '未编号图表'}",
                        figure.caption or ResearchPaperReportRenderer._missing_text(),
                        "",
                        "正文引用：",
                        "\n".join(
                            f"- {item}" for item in figure.referenced_text_spans
                        )
                        or f"- {ResearchPaperReportRenderer._missing_text()}",
                    ]
                )
                for figure in draft.figures
            )
        return sections
