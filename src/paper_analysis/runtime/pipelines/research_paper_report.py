from __future__ import annotations

import re

from pydantic import ValidationError

from paper_analysis.domain.models import (
    FactCheckBatch,
    FigureAnalysis,
    FigureEvidence,
    PaperAnalysis,
)
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument


class ResearchPaperReportRenderer:
    """研究论文 Markdown 报告渲染器（纯函数式，不持有运行状态）。"""

    def render(
        self,
        *,
        source_document: ParsedDocument,
        result: AnalysisResult,
        selected_sections: list[str],
        figure_evidence: list[FigureEvidence],
        figure_analyses: list[FigureAnalysis],
        fact_checks: FactCheckBatch,
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

## 7. 事实检查
### 7.1 总体结论
{self._clean_text(fact_checks.overall_assessment)}

### 7.2 逐项核验
{self._render_fact_checks(fact_checks)}

## 8. 评价
### 8.1 优点
{self._render_bullet_list(paper_analysis.strengths)}

### 8.2 局限性
{self._render_bullet_list(paper_analysis.limitations)}

### 8.3 可复现性
{self._clean_text(paper_analysis.reproducibility)}

## 9. 启发与参考价值
### 9.1 适用场景
{self._render_applicable_scenarios(
    paper_analysis=paper_analysis,
    source_document=source_document,
)}

### 9.2 对当前研究的启发
{self._render_inspiration(paper_analysis=paper_analysis, result=result)}

## 10. 总结
{self._clean_text(result.summary)}
"""

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

    @classmethod
    def _render_figure_evidence_section(cls, figure_evidence: list[FigureEvidence]) -> str:
        if not figure_evidence:
            return cls._missing_text()

        blocks: list[str] = []
        for evidence in figure_evidence:
            metrics = ", ".join(evidence.metrics_or_axes) or cls._missing_text()
            direct_evidence = (
                "\n".join(f"- {item}" for item in evidence.direct_evidence)
                if evidence.direct_evidence
                else f"- {cls._missing_text()}"
            )
            blocks.append(
                "\n".join(
                    [
                        f"### {evidence.figure_id or '未编号图表'}",
                        f"- **图注摘要：** {evidence.figure_title_or_caption or cls._missing_text()}",
                        f"- **图类型：** {evidence.figure_type or cls._missing_text()}",
                        f"- **指标 / 坐标：** {metrics}",
                        f"- **证据质量：** {evidence.evidence_quality or cls._missing_text()}",
                        "- **直接证据：**",
                        direct_evidence,
                    ]
                )
            )
        return "\n\n".join(blocks)

    @classmethod
    def _render_figure_analysis_section(cls, figure_analyses: list[FigureAnalysis]) -> str:
        if not figure_analyses:
            return cls._missing_text()

        blocks: list[str] = []
        for analysis in figure_analyses:
            compared = ", ".join(analysis.compared_items) or cls._missing_text()
            metrics = ", ".join(analysis.metrics_or_axes) or cls._missing_text()
            observations = (
                "\n".join(f"- {item}" for item in analysis.main_observations)
                if analysis.main_observations
                else f"- {cls._missing_text()}"
            )
            blocks.append(
                "\n".join(
                    [
                        f"### {analysis.figure_id or '未编号图表'}",
                        f"- **图注：** {analysis.figure_title_or_caption or cls._missing_text()}",
                        f"- **实验焦点：** {analysis.experiment_focus or cls._missing_text()}",
                        f"- **比较对象：** {compared}",
                        f"- **指标 / 坐标：** {metrics}",
                        "- **主要观察：**",
                        observations,
                        f"- **作者结论：** {analysis.claimed_conclusion or cls._missing_text()}",
                        f"- **置信度：** {analysis.confidence or cls._missing_text()}",
                    ]
                )
            )
        return "\n\n".join(blocks)

    @classmethod
    def _render_figure_conclusions(cls, figure_analyses: list[FigureAnalysis]) -> str:
        bullets = [
            (
                f"- {cls._clean_text(analysis.figure_id or '未编号图表')}："
                f"{cls._clean_text(analysis.claimed_conclusion)}"
            )
            for analysis in figure_analyses
            if analysis.claimed_conclusion
        ]
        return "\n".join(bullets) if bullets else cls._missing_text()

    @classmethod
    def _render_figure_consistency_checks(cls, figure_analyses: list[FigureAnalysis]) -> str:
        bullets = [
            (
                f"- {cls._clean_text(analysis.figure_id or '未编号图表')}："
                f"{cls._clean_text(analysis.consistency_check)}"
                f"（置信度：{cls._clean_text(analysis.confidence)}）"
            )
            for analysis in figure_analyses
        ]
        return "\n".join(bullets) if bullets else cls._missing_text()

    @classmethod
    def _render_fact_checks(cls, fact_checks: FactCheckBatch) -> str:
        if not fact_checks.checks and not fact_checks.rule_flags:
            return cls._missing_text()
        verdict_labels = {
            "supported": "有证据支持",
            "partially_supported": "部分支持",
            "unsupported": "缺少支持",
            "conflicting": "存在冲突",
            "unverifiable": "无法核验",
        }
        blocks: list[str] = []
        for check in fact_checks.checks:
            verdict = verdict_labels.get(check.verdict, check.verdict or "无法核验")
            evidence = "；".join(cls._clean_list(check.evidence_refs)) or cls._missing_text()
            evidence_ids = "、".join(cls._clean_list(check.evidence_ids))
            blocks.append(
                "\n".join(
                    [
                        f"- **{cls._clean_text(check.claim_id or '未编号主张')}｜{verdict}**：{cls._clean_text(check.claim)}",
                        f"  - 依据：{evidence}",
                        f"  - 证据 ID：{evidence_ids or cls._missing_text()}",
                        f"  - 说明：{cls._clean_text(check.rationale)}",
                    ]
                )
            )
        if fact_checks.rule_flags:
            flags = "\n".join(f"  - {cls._clean_text(flag)}" for flag in fact_checks.rule_flags)
            blocks.append(f"- **规则预检查提示**：\n{flags}")
        return "\n".join(blocks)

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
