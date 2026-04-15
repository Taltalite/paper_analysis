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

        key_points = "\n".join(f"- {item}" for item in result.key_points) or "- N/A"
        limitations = "\n".join(f"- {item}" for item in result.limitations) or "- N/A"
        structured_sections = self._render_structured_data(result.structured_data)
        return f"""# {self._profile.markdown_title}

## Title
{result.title or 'N/A'}

## Summary
{result.summary or 'N/A'}

## Key Points
{key_points}

## Limitations
{limitations}

## Structured Data
{structured_sections}
"""

    @staticmethod
    def _render_structured_data(payload: dict[str, object]) -> str:
        if not payload:
            return "N/A"

        blocks: list[str] = []
        for key, value in payload.items():
            heading = key.replace("_", " ").title()
            if isinstance(value, list):
                rendered = "\n".join(f"- {item}" for item in value) or "- N/A"
            elif isinstance(value, dict):
                rendered = "\n".join(
                    f"- **{child_key.replace('_', ' ').title()}:** {child_value}"
                    for child_key, child_value in value.items()
                ) or "- N/A"
            else:
                rendered = str(value) if value else "N/A"
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

        authors = ", ".join(analysis.metadata.authors) if analysis.metadata.authors else "N/A"
        datasets = (
            ", ".join(analysis.extracted_notes.datasets)
            if analysis.extracted_notes.datasets
            else "N/A"
        )
        strengths = "\n".join(f"- {item}" for item in analysis.strengths) or "- N/A"
        limitations = "\n".join(f"- {item}" for item in analysis.limitations) or "- N/A"

        return f"""# Paper Analysis Report

## Metadata
- **Title:** {analysis.metadata.title or result.title or 'N/A'}
- **Authors:** {authors}
- **Venue:** {analysis.metadata.venue or 'N/A'}
- **Year:** {analysis.metadata.year or 'N/A'}

## Research Problem
{analysis.extracted_notes.research_problem or 'N/A'}

## Core Method
{analysis.extracted_notes.core_method or 'N/A'}

## Datasets
{datasets}

## Experimental Setup
{analysis.extracted_notes.experimental_setup or 'N/A'}

## Main Results
{analysis.extracted_notes.main_results or 'N/A'}

## Novelty
{analysis.novelty or 'N/A'}

## Strengths
{strengths}

## Limitations
{limitations}

## Reproducibility
{analysis.reproducibility or 'N/A'}

## Interview Pitch
{analysis.interview_pitch or result.summary or 'N/A'}
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
