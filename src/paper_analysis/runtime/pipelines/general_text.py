from __future__ import annotations

from pydantic import ValidationError

from paper_analysis.domain.models import PaperAnalysis
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.crews.base import (
    CrewAITwoAgentTextAnalysisRunner,
    TextAnalysisCrewRunner,
)
from paper_analysis.runtime.pipelines.base import AnalysisPipeline
from paper_analysis.runtime.pipelines.profiles import GENERAL_TEXT_PROFILE, TextAnalysisProfile


class GeneralTextPipeline(AnalysisPipeline):
    def __init__(
        self,
        *,
        profile: TextAnalysisProfile = GENERAL_TEXT_PROFILE,
        crew_runner: TextAnalysisCrewRunner | None = None,
    ) -> None:
        self._profile = profile
        self._crew_runner = crew_runner or CrewAITwoAgentTextAnalysisRunner()

    async def run(self, document: ParsedDocument) -> AnalysisResult:
        result = self._crew_runner.run(document=document, profile=self._profile)
        if self._looks_like_paper_result(result):
            result.structured_data = self._normalize_paper_structured_data(result.structured_data)
            if not result.summary:
                interview_pitch = result.structured_data.get("interview_pitch")
                if isinstance(interview_pitch, str) and interview_pitch:
                    result.summary = interview_pitch
        if not result.title:
            result.title = document.title
        if not result.markdown_report:
            result.markdown_report = self._build_markdown_report(result)
        return result

    def _build_markdown_report(self, result: AnalysisResult) -> str:
        paper_markdown = self._build_paper_markdown_report(result)
        if paper_markdown is not None:
            return paper_markdown

        key_points = "\n".join(f"- {item}" for item in result.key_points) or f"- {self._missing_text()}"
        limitations = "\n".join(f"- {item}" for item in result.limitations) or f"- {self._missing_text()}"
        structured_sections = self._render_structured_data(result.structured_data)
        return f"""# {self._profile.markdown_title}

## 标题
{result.title or self._missing_text()}

## 摘要
{result.summary or self._missing_text()}

## 要点
{key_points}

## 局限性
{limitations}

## 结构化信息
{structured_sections}
"""

    @classmethod
    def _render_structured_data(cls, payload: dict[str, object]) -> str:
        if not payload:
            return cls._missing_text()

        blocks: list[str] = []
        for key, value in payload.items():
            if key == "interview_pitch":
                continue
            heading = cls._localized_heading(key)
            if isinstance(value, list):
                rendered = "\n".join(f"- {item}" for item in value) or f"- {cls._missing_text()}"
            elif isinstance(value, dict):
                rendered = "\n".join(
                    f"- **{cls._localized_heading(child_key)}：** {child_value or cls._missing_text()}"
                    for child_key, child_value in value.items()
                ) or f"- {cls._missing_text()}"
            else:
                rendered = str(value) if value else cls._missing_text()
            blocks.append(f"### {heading}\n{rendered}")
        return "\n\n".join(blocks)

    @staticmethod
    def _looks_like_paper_result(result: AnalysisResult) -> bool:
        required_keys = {
            "metadata",
            "extracted_notes",
            "novelty",
            "strengths",
            "limitations",
            "reproducibility",
            "interview_pitch",
        }
        return required_keys.issubset(result.structured_data)

    @classmethod
    def _build_paper_markdown_report(cls, result: AnalysisResult) -> str | None:
        if not cls._looks_like_paper_result(result):
            return None

        try:
            analysis = PaperAnalysis.model_validate(result.structured_data)
        except ValidationError:
            return None

        authors = ", ".join(analysis.metadata.authors) if analysis.metadata.authors else cls._missing_text()
        datasets = (
            ", ".join(analysis.extracted_notes.datasets)
            if analysis.extracted_notes.datasets
            else cls._missing_text()
        )
        strengths = "\n".join(f"- {item}" for item in analysis.strengths) or f"- {cls._missing_text()}"
        limitations = "\n".join(f"- {item}" for item in analysis.limitations) or f"- {cls._missing_text()}"

        return f"""# 论文分析报告

## 基础信息
- **标题：** {analysis.metadata.title or result.title or cls._missing_text()}
- **作者：** {authors}
- **期刊/会议：** {analysis.metadata.venue or cls._missing_text()}
- **年份：** {analysis.metadata.year or cls._missing_text()}

## 研究问题
{analysis.extracted_notes.research_problem or cls._missing_text()}

## 核心方法
{analysis.extracted_notes.core_method or cls._missing_text()}

## 数据集
{datasets}

## 实验设置
{analysis.extracted_notes.experimental_setup or cls._missing_text()}

## 主要结果
{analysis.extracted_notes.main_results or cls._missing_text()}

## 创新点
{analysis.novelty or cls._missing_text()}

## 优点
{strengths}

## 局限性
{limitations}

## 复现建议
{analysis.reproducibility or cls._missing_text()}
"""

    @staticmethod
    def _normalize_paper_structured_data(payload: dict[str, object]) -> dict[str, object]:
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        extracted_notes = (
            payload.get("extracted_notes")
            if isinstance(payload.get("extracted_notes"), dict)
            else {}
        )
        return {
            "metadata": {
                "title": GeneralTextPipeline._string_value(metadata.get("title")),
                "authors": GeneralTextPipeline._list_value(metadata.get("authors")),
                "venue": GeneralTextPipeline._string_value(metadata.get("venue")),
                "year": GeneralTextPipeline._string_value(metadata.get("year")),
            },
            "extracted_notes": {
                "research_problem": GeneralTextPipeline._string_value(
                    extracted_notes.get("research_problem")
                ),
                "core_method": GeneralTextPipeline._string_value(
                    extracted_notes.get("core_method")
                ),
                "datasets": GeneralTextPipeline._list_value(extracted_notes.get("datasets")),
                "experimental_setup": GeneralTextPipeline._string_value(
                    extracted_notes.get("experimental_setup")
                ),
                "main_results": GeneralTextPipeline._string_value(
                    extracted_notes.get("main_results")
                ),
            },
            "novelty": GeneralTextPipeline._string_value(payload.get("novelty")),
            "strengths": GeneralTextPipeline._list_value(payload.get("strengths")),
            "limitations": GeneralTextPipeline._list_value(payload.get("limitations")),
            "reproducibility": GeneralTextPipeline._string_value(payload.get("reproducibility")),
            "interview_pitch": GeneralTextPipeline._string_value(payload.get("interview_pitch")),
        }

    @staticmethod
    def _string_value(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return " ".join(str(item).strip() for item in value if str(item).strip()).strip()
        return str(value).strip()

    @staticmethod
    def _list_value(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        rendered = str(value).strip()
        return [rendered] if rendered else []

    @staticmethod
    def _missing_text() -> str:
        return "未明确说明"

    @staticmethod
    def _localized_heading(key: str) -> str:
        mapping = {
            "metadata": "基础信息",
            "title": "标题",
            "authors": "作者",
            "venue": "期刊/会议",
            "year": "年份",
            "extracted_notes": "提取要点",
            "research_problem": "研究问题",
            "core_method": "核心方法",
            "datasets": "数据集",
            "experimental_setup": "实验设置",
            "main_results": "主要结果",
            "novelty": "创新点",
            "strengths": "优点",
            "limitations": "局限性",
            "reproducibility": "复现建议",
            "interview_pitch": "面试表达",
            "sections": "章节信息",
            "selected_sections": "重点章节",
            "source_structure": "源文档结构",
            "parser_kind": "解析器类型",
            "page_count": "页数",
            "doi": "DOI",
            "section_order": "章节顺序",
            "summary": "摘要",
            "key_points": "要点",
            "markdown_report": "Markdown 报告",
            "structured_data": "结构化信息",
        }
        return mapping.get(key, key.replace("_", " ").title())
