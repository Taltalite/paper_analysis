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
from paper_analysis.runtime.pipelines.quality_control import apply_quality_gate
from paper_analysis.runtime.pipelines.research_products import build_research_products


class ResearchPaperReportRenderer:
    """在实际交付入口执行确定性 QC，确保 Markdown 与 JSON 使用同一份质量状态。"""

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
        figure_analyses = apply_quality_gate(
            document=source_document, result=result, figure_analyses=figure_analyses,
            figure_evidence=figure_evidence, fact_checks=fact_checks,
        )
        products = build_research_products(
            document=source_document,
            result=result,
            figure_evidence=figure_evidence,
            figure_analyses=figure_analyses,
        )
        result.research_products = products
        result.structured_data["research_products"] = products.model_dump(mode="json")
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

{self._render_quality(result)}

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

### 6.4 视觉证据与解析状态
以下为解析器线索与模型视觉提取记录，不代表独立核验通过。
{self._render_figure_evidence_section(figure_evidence)}

## 7. 事实检查
### 7.1 总体结论
以下为模型核验意见，交付状态以报告顶部 QC 结果为准。
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

## 11. 领域结构化产物
以下产物由已解析证据、主张清单和 QC 结果确定性组装；`verified` 仅表示通过本项目的引用/定位闸门，不代表专家正确性认证。
{self._render_research_products(products)}

{self._render_draft(result)}
"""

    @staticmethod
    def _render_quality(result: AnalysisResult) -> str:
        qc = result.quality
        if qc is None:
            return "> QC 尚未执行。"
        labels = {"passed": "通过本轮检查", "needs_review": "需要复核", "blocked": "暂不能交付正式结论"}
        lines = [
            f"> **QC：{labels[qc.status]}**",
            f"> 有效清单中已对应核验 {qc.checked_claims}/{qc.expected_claims} 条主张；另有结构无效 {qc.invalid_claims} 条；可交付 {len(qc.accepted_claim_ids)} 条。",
            f"> {qc.scope}",
            "\n### QC 问题清单",
        ]
        codes = list(dict.fromkeys(item.code for item in qc.issues))
        for code in codes:
            issues = [item for item in qc.issues if item.code == code]
            lines.append(f"- **{code}（{len(issues)} 项）**")
            lines.extend(f"  - `{item.location}`：{item.message}" for item in issues[:3])
            if len(issues) > 3:
                lines.append("  - 其余位置见 JSON 的 quality.issues。")
        if not qc.issues:
            lines.append("- 本轮未检出问题；仍需结合检查范围理解。")
        return "\n".join(lines)

    @classmethod
    def _render_research_products(cls, products) -> str:  # noqa: ANN001
        coverage = products.coverage
        lines = [
            f"### 11.1 覆盖状态\n- 候选章节：{len(coverage.candidate.sections)}；已读取：{len(coverage.read.sections)}；已核验主张：{len(coverage.verified.claims)}/{len(coverage.candidate.claims)}。",
            f"- 候选图表：{len(coverage.candidate.figures)}；已选择：{len(coverage.selected.figures)}；已有直接复核支持：{len(coverage.verified.figures)}。",
            "### 11.2 故事架构",
        ]
        if products.story.nodes:
            lines.extend(
                f"- `{node.node_id}`（{node.role}，{node.verification_status.value}）：{cls._clean_text(node.statement)}"
                for node in products.story.nodes
            )
        else:
            lines.append("- 未形成可定位的故事节点。")
        if products.story.edges:
            lines.append("- 结构边：" + "；".join(
                f"{edge.source} → {edge.target}（{edge.relation}）" for edge in products.story.edges
            ))
        lines.append("### 11.3 图组 Flow")
        if products.figure_flow.nodes:
            lines.extend(
                f"- `{node.figure}`（{node.coverage_status.value}）：{cls._clean_text(node.role)}"
                for node in products.figure_flow.nodes
            )
            lines.extend(f"- {edge.source} → {edge.target}：{cls._clean_text(edge.relation)}；证据：{'、'.join(edge.evidence_ids)}"
                         for edge in products.figure_flow.edges)
            if not products.figure_flow.edges:
                lines.append("- 尚无通过核验的图间论证关系，不根据图号顺序补充连线。")
        else:
            lines.append("- 未形成可定位的图组节点。")
        lines.append("### 11.4 细节证据")
        if products.evidence_matrix:
            lines.extend(
                f"- `{row.finding_id}`：{cls._clean_text(row.statement)}；样本/条件/重复/对照：{row.sample_or_system} / {row.condition} / {row.replicates} / {row.controls}；证据 ID：{'、'.join(row.evidence_ids) or '未明确说明'}"
                for row in products.evidence_matrix
            )
        else:
            lines.append("- 未形成细节证据矩阵。")
        lines.append("### 11.5 Benchmark")
        if products.benchmark.status != "available":
            lines.append(f"- `{products.benchmark.status.value if hasattr(products.benchmark.status, 'value') else products.benchmark.status}`：{cls._clean_text(products.benchmark.reason)}")
        else:
            lines.extend(
                f"- {entry.method}｜{entry.dataset}｜{entry.task}｜{entry.metric}：{entry.value_raw or '未报告'}（{entry.direction.value}；证据：{'、'.join(entry.evidence_ids) or '未明确说明'}）"
                for entry in products.benchmark.entries
            )
        return "\n".join(lines)

    @classmethod
    def _render_draft(cls, result: AnalysisResult) -> str:
        draft = result.structured_data.get("qc_draft", {})
        sections = draft.get("structured_data", {})
        fields = {"原始摘要": draft.get("summary", ""), "原始要点": draft.get("key_points", []),
                  "原始提取": sections.get("extracted_notes", {}), "原始创新点": sections.get("novelty", "")}
        blocks = ["## 附录：原始生成草稿（待复核，不作为正式结论）", "完整原始结构保存在 JSON 的 qc_draft 中。"]
        for label, value in fields.items():
            if not value:
                continue
            text = str(value)
            if len(text) > 3000:
                text = text[:3000] + "\n（展示已截断，完整内容见 JSON）"
            blocks.append(f"### {label}\n" + "\n".join(f"> {line}" for line in text.splitlines()))
        return "\n\n".join(blocks)

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
                        f"#### {evidence.figure_id or '未编号图表'}",
                        f"- **图注摘要：** {evidence.figure_title_or_caption or cls._missing_text()}",
                        f"- **图类型：** {evidence.figure_type or cls._missing_text()}",
                        f"- **视觉解析：** {'已调用多模态模型（含缓存结果）' if evidence.semantic_source == 'multimodal_llm' else '未完成视觉识别，仅使用图注和正文线索'}",
                        f"- **指标 / 坐标：** {metrics}",
                        f"- **可见文字：** {'；'.join(evidence.visible_text) or cls._missing_text()}",
                        f"- **图例：** {'；'.join(evidence.legend_items) or cls._missing_text()}",
                        f"- **子图：** {'；'.join(f'{panel.panel_label}: {panel.summary}' for panel in evidence.panels) or cls._missing_text()}",
                        f"- **不确定性：** {'；'.join(evidence.uncertainties) or '未报告'}",
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
        if result.quality is not None:
            return "\n".join(f"> {line}" for line in result.summary.splitlines())
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
