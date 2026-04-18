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
        parser_authors = source_document.metadata.get("authors", [])
        if isinstance(parser_authors, list):
            fallback_authors = parser_authors
        else:
            fallback_authors = [str(parser_authors)] if parser_authors else []
        authors = ", ".join(
            self._clean_list(paper_analysis.metadata.authors or fallback_authors)
        ) or self._missing_text()

        return f"""# 文献分析报告

## 1. 基本信息
- 标题：{self._clean_text(paper_analysis.metadata.title or source_document.title)}
- 作者：{authors}
- 发表平台：{self._clean_text(paper_analysis.metadata.venue or source_document.metadata.get('venue'))}
- 年份：{self._clean_text(paper_analysis.metadata.year or source_document.metadata.get('year'))}

## 2. 摘要式总结
{self._build_summary_blockquote(paper_analysis=paper_analysis, result=result)}

## 3. 研究问题
### 3.1 背景
{self._derive_background(
    result=result,
    source_document=source_document,
    selected_sections=selected_sections,
)}

### 3.2 论文要解决的问题
{self._clean_text(paper_analysis.extracted_notes.research_problem)}

## 4. 方法
### 4.1 方法概述
{self._clean_text(paper_analysis.extracted_notes.core_method)}

### 4.2 关键模块
{self._render_bullet_list(result.key_points)}

### 4.3 创新点
{self._clean_text(paper_analysis.novelty)}

## 5. 实验与结果
### 5.1 实验设置
{self._render_experimental_setup(paper_analysis)}

### 5.2 主要结果
{self._clean_text(paper_analysis.extracted_notes.main_results)}

### 5.3 与基线对比
{self._render_baseline_comparison(figure_analyses)}

### 5.4 作者结论
{self._render_author_conclusion(result=result, paper_analysis=paper_analysis)}

## 6. 图表分析
### 6.1 关键图表
{self._render_key_figures(figure_analyses, figure_evidence)}

### 6.2 图中结论
{self._render_figure_conclusions(figure_analyses)}

### 6.3 图文一致性
{self._render_figure_consistency_checks(figure_analyses)}

## 7. 评价
### 7.1 优点
{self._render_bullet_list(paper_analysis.strengths)}

### 7.2 局限性
{self._render_bullet_list(paper_analysis.limitations)}

### 7.3 可复现性
{self._clean_text(paper_analysis.reproducibility)}

## 8. 启发与参考价值
### 8.1 适用场景
{self._render_applicable_scenarios(
    paper_analysis=paper_analysis,
    source_document=source_document,
)}

### 8.2 对当前研究的启发
{self._render_inspiration(paper_analysis=paper_analysis, result=result)}

## 9. 总结
{self._clean_text(result.summary)}
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
            (
                f"- {ResearchPaperPipeline._clean_text(analysis.figure_id or '未编号图表')}："
                f"{ResearchPaperPipeline._clean_text(analysis.claimed_conclusion)}"
            )
            for analysis in figure_analyses
            if analysis.claimed_conclusion
        ]
        return "\n".join(bullets) if bullets else ResearchPaperPipeline._missing_text()

    @staticmethod
    def _render_figure_consistency_checks(figure_analyses: list[FigureAnalysis]) -> str:
        bullets = [
            (
                f"- {ResearchPaperPipeline._clean_text(analysis.figure_id or '未编号图表')}："
                f"{ResearchPaperPipeline._clean_text(analysis.consistency_check)}"
                f"（置信度：{ResearchPaperPipeline._clean_text(analysis.confidence)}）"
            )
            for analysis in figure_analyses
        ]
        return "\n".join(bullets) if bullets else ResearchPaperPipeline._missing_text()

    @classmethod
    def _build_summary_blockquote(
        cls,
        *,
        paper_analysis: PaperAnalysis,
        result: AnalysisResult,
    ) -> str:
        research_problem = cls._clean_text(paper_analysis.extracted_notes.research_problem)
        core_method = cls._clean_text(paper_analysis.extracted_notes.core_method)
        main_results = cls._clean_text(paper_analysis.extracted_notes.main_results)
        fallback_summary = cls._clean_text(result.summary)

        lines = [
            f"> 这篇论文主要研究{research_problem}。",
            f"> 核心方法是{core_method}。",
            f"> 主要结果表明{main_results}。",
        ]
        if research_problem == cls._missing_text() and fallback_summary != cls._missing_text():
            lines[0] = f"> 这篇论文主要研究内容可概括为：{fallback_summary}"
        return "\n".join(lines)

    @classmethod
    def _derive_background(
        cls,
        *,
        result: AnalysisResult,
        source_document: ParsedDocument,
        selected_sections: list[str],
    ) -> str:
        candidates: list[str] = []
        if result.key_points:
            candidates.extend(result.key_points)
        for section_name in ("abstract", "introduction"):
            if section_name in selected_sections and source_document.sections.get(section_name):
                candidates.append(source_document.sections[section_name][:220])
        for candidate in candidates:
            cleaned = cls._clean_text(candidate)
            if cleaned != cls._missing_text():
                return cleaned
        return cls._missing_text()

    @classmethod
    def _render_bullet_list(cls, items: list[str]) -> str:
        cleaned_items = cls._clean_list(items)
        if not cleaned_items:
            return cls._missing_text()
        return "\n".join(f"- {item}" for item in cleaned_items)

    @classmethod
    def _render_experimental_setup(cls, paper_analysis: PaperAnalysis) -> str:
        setup = cls._clean_text(paper_analysis.extracted_notes.experimental_setup)
        datasets = cls._clean_list(paper_analysis.extracted_notes.datasets)
        if not datasets:
            return setup
        dataset_line = f"涉及数据集：{', '.join(datasets)}。"
        if setup == cls._missing_text():
            return dataset_line
        return f"{setup}\n\n{dataset_line}"

    @classmethod
    def _render_baseline_comparison(cls, figure_analyses: list[FigureAnalysis]) -> str:
        bullets: list[str] = []
        for analysis in figure_analyses:
            compared_items = ", ".join(cls._clean_list(analysis.compared_items))
            observation = cls._clean_text(
                analysis.main_observations[0] if analysis.main_observations else ""
            )
            if compared_items and observation != cls._missing_text():
                bullets.append(
                    f"- {cls._clean_text(analysis.figure_id or '未编号图表')}：比较对象包括 {compared_items}；主要观察为 {observation}"
                )
        return "\n".join(bullets) if bullets else cls._missing_text()

    @classmethod
    def _render_author_conclusion(
        cls,
        *,
        result: AnalysisResult,
        paper_analysis: PaperAnalysis,
    ) -> str:
        main_results = cls._clean_text(paper_analysis.extracted_notes.main_results)
        if main_results != cls._missing_text():
            return main_results
        return cls._clean_text(result.summary)

    @classmethod
    def _render_key_figures(
        cls,
        figure_analyses: list[FigureAnalysis],
        figure_evidence: list[FigureEvidence],
    ) -> str:
        bullets: list[str] = []
        seen_ids: set[str] = set()
        for analysis in figure_analyses:
            figure_id = cls._clean_text(analysis.figure_id or "未编号图表")
            seen_ids.add(figure_id)
            bullets.append(f"- {figure_id}：{cls._clean_text(analysis.figure_title_or_caption)}")
        for evidence in figure_evidence:
            figure_id = cls._clean_text(evidence.figure_id or "未编号图表")
            if figure_id in seen_ids:
                continue
            bullets.append(f"- {figure_id}：{cls._clean_text(evidence.figure_title_or_caption)}")
        return "\n".join(bullets) if bullets else cls._missing_text()

    @classmethod
    def _render_applicable_scenarios(
        cls,
        *,
        paper_analysis: PaperAnalysis,
        source_document: ParsedDocument,
    ) -> str:
        datasets = cls._clean_list(paper_analysis.extracted_notes.datasets)
        if datasets:
            return f"该方法可优先参考于与 {', '.join(datasets)} 类似的数据或任务场景。"
        venue = cls._clean_text(paper_analysis.metadata.venue or source_document.metadata.get("venue"))
        if venue != cls._missing_text():
            return f"可优先用于与 {venue} 相关的研究问题与实验设计参考。"
        return cls._missing_text()

    @classmethod
    def _render_inspiration(
        cls,
        *,
        paper_analysis: PaperAnalysis,
        result: AnalysisResult,
    ) -> str:
        novelty = cls._clean_text(paper_analysis.novelty)
        if novelty != cls._missing_text():
            return novelty
        cleaned_points = cls._clean_list(result.key_points)
        if cleaned_points:
            return cleaned_points[0]
        return cls._missing_text()

    @classmethod
    def _clean_list(cls, values: list[str]) -> list[str]:
        items: list[str] = []
        for value in values:
            cleaned = cls._clean_text(value)
            if cleaned != cls._missing_text():
                items.append(cleaned)
        return items

    @classmethod
    def _clean_text(cls, value: object) -> str:
        if value is None:
            return cls._missing_text()
        rendered = str(value).strip()
        if not rendered:
            return cls._missing_text()

        rendered = re.sub(r"^\s*#{1,6}\s*", "", rendered, flags=re.MULTILINE)
        rendered = re.sub(r"^\s*[-*]\s*", "", rendered, flags=re.MULTILINE)
        rendered = re.sub(r"\n{3,}", "\n\n", rendered)
        return rendered.strip() or cls._missing_text()

    @staticmethod
    def _missing_text() -> str:
        return "未明确说明"
