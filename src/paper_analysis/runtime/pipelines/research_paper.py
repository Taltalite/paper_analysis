from __future__ import annotations

import re

from pydantic import ValidationError

from paper_analysis.domain.models import (
    DocumentStructureDraft,
    FigureAnalysis,
    FigureAnalysisBatch,
    FigureEvidence,
    FigureEvidenceBatch,
    FigureMetadata,
    FigureSemanticArtifact,
    FigureSemanticArtifactBatch,
    PaperAnalysis,
)
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.crews.base import TextAnalysisCrewRunner
from paper_analysis.runtime.crews.research import (
    DocumentStructuringRunner,
    FigureAnalysisRunner,
    FigureEvidenceCuratorRunner,
    FigureGroundingRunner,
)
from paper_analysis.runtime.pipelines.general_text import GeneralTextPipeline
from paper_analysis.runtime.pipelines.base import AnalysisPipeline
from paper_analysis.runtime.pipelines.profiles import RESEARCH_PAPER_PROFILE


class ResearchPaperPipeline(AnalysisPipeline):
    def __init__(
        self,
        *,
        crew_runner: TextAnalysisCrewRunner | None = None,
        structuring_runner: DocumentStructuringRunner | None = None,
        figure_grounding_runner: FigureGroundingRunner | None = None,
        figure_evidence_curator: FigureEvidenceCuratorRunner | None = None,
        figure_runner: FigureAnalysisRunner | None = None,
    ) -> None:
        self._pipeline = GeneralTextPipeline(
            profile=RESEARCH_PAPER_PROFILE,
            crew_runner=crew_runner,
        )
        self._structuring_runner = structuring_runner
        self._figure_grounding_runner = figure_grounding_runner
        self._figure_evidence_curator = figure_evidence_curator
        self._figure_runner = figure_runner

    async def run(self, document: ParsedDocument) -> AnalysisResult:
        source_document = self._refine_document_structure(document)
        focused_document, selected_sections = self._build_focus_document(source_document)
        result = await self._pipeline.run(focused_document)
        semantic_artifacts, figure_evidence, figure_analyses = self._run_figure_pipeline(
            source_document=source_document,
            selected_sections=selected_sections,
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
            "selected_sections": selected_sections,
            "source_structure": {
                "parser_kind": source_document.metadata.get("parser_kind", "unknown"),
                "page_count": source_document.metadata.get("page_count"),
                "doi": source_document.metadata.get("doi", ""),
                "section_order": source_document.section_order,
                "figure_count": len(source_document.figures),
            },
        }
        result.markdown_report = self._build_report(
            source_document=source_document,
            result=result,
            selected_sections=selected_sections,
            figure_evidence=figure_evidence,
            figure_analyses=figure_analyses,
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

    def _build_report(
        self,
        *,
        source_document: ParsedDocument,
        result: AnalysisResult,
        selected_sections: list[str],
        figure_evidence: list[FigureEvidence],
        figure_analyses: list[FigureAnalysis],
    ) -> str:
        paper_analysis = self._coerce_paper_analysis(result)
        source_section_preview = self._render_source_section_preview(source_document, selected_sections)
        figure_evidence_section = self._render_figure_evidence_section(figure_evidence)
        figure_analysis_section = self._render_figure_analysis_section(figure_analyses)
        figure_conclusions_section = self._render_figure_conclusions(figure_analyses)
        figure_consistency_section = self._render_figure_consistency_checks(figure_analyses)
        selected_text = "\n".join(
            f"- {self._localized_section_name(section)}" for section in selected_sections
        ) or "- 回退到原始文本片段"
        parser_authors = source_document.metadata.get("authors", [])
        if isinstance(parser_authors, list):
            fallback_authors = parser_authors
        else:
            fallback_authors = [str(parser_authors)] if parser_authors else []
        authors = ", ".join(paper_analysis.metadata.authors or fallback_authors) or self._missing_text()
        strengths = "\n".join(f"- {item}" for item in paper_analysis.strengths) or f"- {self._missing_text()}"
        limitations = "\n".join(f"- {item}" for item in paper_analysis.limitations) or f"- {self._missing_text()}"
        datasets = ", ".join(paper_analysis.extracted_notes.datasets) or self._missing_text()

        return f"""# 研究型文献分析报告

## 来源文档
- **标题：** {paper_analysis.metadata.title or source_document.title or self._missing_text()}
- **作者：** {authors}
- **DOI：** {source_document.metadata.get('doi') or self._missing_text()}
- **期刊/会议：** {paper_analysis.metadata.venue or source_document.metadata.get('venue') or self._missing_text()}
- **年份：** {paper_analysis.metadata.year or source_document.metadata.get('year') or self._missing_text()}
- **页数：** {source_document.metadata.get('page_count') or self._missing_text()}

## 参与分析的重点章节
{selected_text}

## 结构化解析预览
{source_section_preview}

## 研究问题
{paper_analysis.extracted_notes.research_problem or self._missing_text()}

## 核心方法
{paper_analysis.extracted_notes.core_method or self._missing_text()}

## 数据集
{datasets}

## 实验设置
{paper_analysis.extracted_notes.experimental_setup or self._missing_text()}

## 主要结果
{paper_analysis.extracted_notes.main_results or self._missing_text()}

## 创新点
{paper_analysis.novelty or self._missing_text()}

## 优点
{strengths}

## 局限性
{limitations}

## 复现建议
{paper_analysis.reproducibility or self._missing_text()}

## 图像语义证据摘要
{figure_evidence_section}

## 图像实验结果分析
{figure_analysis_section}

## 关键图表结论
{figure_conclusions_section}

## 图文一致性检查
{figure_consistency_section}

## 总结
{result.summary or self._missing_text()}
"""

    def _refine_document_structure(self, document: ParsedDocument) -> ParsedDocument:
        if document.metadata.get("parser_kind") != "pdf":
            return document

        draft = self._coarse_structure_draft(document)
        if self._structuring_runner is not None:
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

    @staticmethod
    def _render_source_section_preview(
        source_document: ParsedDocument,
        selected_sections: list[str],
    ) -> str:
        if not selected_sections:
            return ResearchPaperPipeline._missing_text()

        blocks: list[str] = []
        for section_name in selected_sections:
            content = source_document.sections.get(section_name, "").strip()
            if not content:
                continue
            preview = content[:700].strip()
            heading = ResearchPaperPipeline._localized_section_name(section_name)
            blocks.append(f"### {heading}\n{preview}")
        return "\n\n".join(blocks) if blocks else ResearchPaperPipeline._missing_text()

    @staticmethod
    def _coerce_paper_analysis(result: AnalysisResult) -> PaperAnalysis:
        payload = {
            key: value
            for key, value in result.structured_data.items()
            if key
            in {
                "metadata",
                "extracted_notes",
                "novelty",
                "strengths",
                "limitations",
                "reproducibility",
                "figure_analyses",
            }
        }
        try:
            return PaperAnalysis.model_validate(payload)
        except ValidationError:
            return PaperAnalysis()

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
                        figure.caption or ResearchPaperPipeline._missing_text(),
                        "",
                        "正文引用：",
                        "\n".join(
                            f"- {item}" for item in figure.referenced_text_spans
                        )
                        or f"- {ResearchPaperPipeline._missing_text()}",
                    ]
                )
                for figure in draft.figures
            )
        return sections

    @staticmethod
    def _render_figure_evidence_section(figure_evidence: list[FigureEvidence]) -> str:
        if not figure_evidence:
            return ResearchPaperPipeline._missing_text()

        blocks: list[str] = []
        for evidence in figure_evidence:
            metrics = ", ".join(evidence.metrics_or_axes) or ResearchPaperPipeline._missing_text()
            direct_evidence = (
                "\n".join(f"- {item}" for item in evidence.direct_evidence)
                if evidence.direct_evidence
                else f"- {ResearchPaperPipeline._missing_text()}"
            )
            blocks.append(
                "\n".join(
                    [
                        f"### {evidence.figure_id or '未编号图表'}",
                        f"- **图注摘要：** {evidence.figure_title_or_caption or ResearchPaperPipeline._missing_text()}",
                        f"- **图类型：** {evidence.figure_type or ResearchPaperPipeline._missing_text()}",
                        f"- **指标 / 坐标：** {metrics}",
                        f"- **证据质量：** {evidence.evidence_quality or ResearchPaperPipeline._missing_text()}",
                        "- **直接证据：**",
                        direct_evidence,
                    ]
                )
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _render_figure_analysis_section(figure_analyses: list[FigureAnalysis]) -> str:
        if not figure_analyses:
            return ResearchPaperPipeline._missing_text()

        blocks: list[str] = []
        for analysis in figure_analyses:
            compared = ", ".join(analysis.compared_items) or ResearchPaperPipeline._missing_text()
            metrics = ", ".join(analysis.metrics_or_axes) or ResearchPaperPipeline._missing_text()
            observations = (
                "\n".join(f"- {item}" for item in analysis.main_observations)
                if analysis.main_observations
                else f"- {ResearchPaperPipeline._missing_text()}"
            )
            blocks.append(
                "\n".join(
                    [
                        f"### {analysis.figure_id or '未编号图表'}",
                        f"- **图注：** {analysis.figure_title_or_caption or ResearchPaperPipeline._missing_text()}",
                        f"- **实验焦点：** {analysis.experiment_focus or ResearchPaperPipeline._missing_text()}",
                        f"- **比较对象：** {compared}",
                        f"- **指标 / 坐标：** {metrics}",
                        "- **主要观察：**",
                        observations,
                        f"- **作者结论：** {analysis.claimed_conclusion or ResearchPaperPipeline._missing_text()}",
                        f"- **置信度：** {analysis.confidence or ResearchPaperPipeline._missing_text()}",
                    ]
                )
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _render_figure_conclusions(figure_analyses: list[FigureAnalysis]) -> str:
        bullets = [
            f"- {analysis.figure_id or '未编号图表'}：{analysis.claimed_conclusion}"
            for analysis in figure_analyses
            if analysis.claimed_conclusion
        ]
        return "\n".join(bullets) if bullets else ResearchPaperPipeline._missing_text()

    @staticmethod
    def _render_figure_consistency_checks(figure_analyses: list[FigureAnalysis]) -> str:
        bullets = [
            f"- {analysis.figure_id or '未编号图表'}：{analysis.consistency_check or ResearchPaperPipeline._missing_text()}（置信度：{analysis.confidence or ResearchPaperPipeline._missing_text()}）"
            for analysis in figure_analyses
        ]
        return "\n".join(bullets) if bullets else ResearchPaperPipeline._missing_text()

    @staticmethod
    def _localized_section_name(section_name: str) -> str:
        mapping = {
            "abstract": "摘要（Abstract）",
            "introduction": "引言（Introduction）",
            "method": "方法（Method）",
            "experimental_setup": "实验设置（Experimental Setup）",
            "results": "结果（Results）",
            "discussion": "讨论（Discussion）",
            "conclusion": "结论（Conclusion）",
            "figures": "图示（Figures）",
        }
        return mapping.get(section_name, section_name.replace("_", " ").title())

    @staticmethod
    def _missing_text() -> str:
        return "未明确说明"
