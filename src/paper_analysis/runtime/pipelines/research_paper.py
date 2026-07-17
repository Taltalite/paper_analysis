from __future__ import annotations

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

    async def run(self, document: ParsedDocument) -> AnalysisResult:
        source_document = self._refine_document_structure(document)
        focused_document, selected_sections = self._build_focus_document(source_document)
        if self._parallel_stages:
            result, figure_outputs = await asyncio.gather(
                self._pipeline.arun(focused_document),
                self._run_figure_pipeline_async(
                    source_document=source_document,
                    selected_sections=selected_sections,
                ),
            )
            semantic_artifacts, figure_evidence, figure_analyses = figure_outputs
        else:
            result = await self._pipeline.run(focused_document)
            semantic_artifacts, figure_evidence, figure_analyses = self._run_figure_pipeline(
                source_document=source_document,
                selected_sections=selected_sections,
            )
        fact_checks = self._run_fact_checks(
            source_document=source_document,
            result=result,
            figure_evidence=figure_evidence,
            figure_analyses=figure_analyses,
        )
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

        chunks: list[str] = []
        total_chars = 0
        for section_name in selected_sections:
            content = document.sections.get(section_name, "").strip()
            if not content:
                continue
            chunk = f"## {section_name.replace('_', ' ').title()}\n{content}"
            if total_chars + len(chunk) > 12000 and chunks:
                break
            chunks.append(chunk)
            total_chars += len(chunk)

        focus_text = "\n\n".join(chunks).strip() or document.raw_text[:12000]
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

    def _refine_document_structure(self, document: ParsedDocument) -> ParsedDocument:
        if document.metadata.get("parser_kind") != "pdf":
            return document

        draft = self._coarse_structure_draft(document)
        if self._structuring_runner is not None and self._needs_structure_refinement(document):
            draft = self._structuring_runner.run(document=document)

        title = draft.title or document.title
        merged_metadata = {
            **document.metadata,
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

    def _run_figure_pipeline(
        self,
        *,
        source_document: ParsedDocument,
        selected_sections: list[str],
    ) -> tuple[list[FigureSemanticArtifact], list[FigureEvidence], list[FigureAnalysis]]:
        if not source_document.figures:
            return [], [], []

        selected_figures = self._select_figures_for_analysis(
            document=source_document,
            selected_sections=selected_sections,
        )
        if not selected_figures:
            return [], [], []

        semantic_batch = self._run_figure_grounding(
            source_document=source_document,
            selected_figures=selected_figures,
        )
        evidence_batch = self._run_figure_evidence_curator(
            source_document=source_document,
            selected_figures=selected_figures,
            semantic_batch=semantic_batch,
        )
        analysis_batch = self._run_figure_analysis(
            source_document=source_document,
            evidence_batch=evidence_batch,
        )
        return semantic_batch.artifacts, evidence_batch.evidences, analysis_batch.analyses

    async def _run_figure_pipeline_async(
        self,
        *,
        source_document: ParsedDocument,
        selected_sections: list[str],
    ) -> tuple[list[FigureSemanticArtifact], list[FigureEvidence], list[FigureAnalysis]]:
        """并行模式下的图表阶段：grounding/curator 为确定性或 adapter 调用，保持同步；
        仅 LLM 图表分析阶段走原生异步，与正文理解并行。"""
        if not source_document.figures:
            return [], [], []

        selected_figures = self._select_figures_for_analysis(
            document=source_document,
            selected_sections=selected_sections,
        )
        if not selected_figures:
            return [], [], []

        semantic_batch = self._run_figure_grounding(
            source_document=source_document,
            selected_figures=selected_figures,
        )
        evidence_batch = self._run_figure_evidence_curator(
            source_document=source_document,
            selected_figures=selected_figures,
            semantic_batch=semantic_batch,
        )
        analysis_batch = await self._run_figure_analysis_async(
            source_document=source_document,
            evidence_batch=evidence_batch,
        )
        return semantic_batch.artifacts, evidence_batch.evidences, analysis_batch.analyses

    async def _run_figure_analysis_async(
        self,
        *,
        source_document: ParsedDocument,
        evidence_batch: FigureEvidenceBatch,
    ) -> FigureAnalysisBatch:
        if self._figure_runner is None or not evidence_batch.evidences:
            return FigureAnalysisBatch()
        arun = getattr(self._figure_runner, "arun", None)
        if callable(arun):
            batch = await arun(document=source_document, figure_evidences=evidence_batch)
        else:
            batch = self._figure_runner.run(
                document=source_document,
                figure_evidences=evidence_batch,
            )
        if isinstance(batch, FigureAnalysisBatch):
            return batch
        return FigureAnalysisBatch()

    def _run_figure_grounding(
        self,
        *,
        source_document: ParsedDocument,
        selected_figures: list[FigureMetadata],
    ) -> FigureSemanticArtifactBatch:
        if self._figure_grounding_runner is None:
            return FigureSemanticArtifactBatch()
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
    ) -> FigureAnalysisBatch:
        if self._figure_runner is None or not evidence_batch.evidences:
            return FigureAnalysisBatch()
        batch = self._figure_runner.run(
            document=source_document,
            figure_evidences=evidence_batch,
        )
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
    ) -> FactCheckBatch:
        if self._fact_check_runner is None:
            return FactCheckBatch(overall_assessment="未配置事实检查 agent。")
        batch = self._fact_check_runner.run(
            document=source_document,
            analysis_result=result,
            figure_analyses=figure_analyses,
            figure_evidence=figure_evidence,
        )
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
        return ranked[:4]

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
