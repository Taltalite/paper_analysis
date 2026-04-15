from __future__ import annotations

from pydantic import ValidationError

from paper_analysis.domain.models import PaperAnalysis
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.crews.base import TextAnalysisCrewRunner
from paper_analysis.runtime.pipelines.general_text import GeneralTextPipeline
from paper_analysis.runtime.pipelines.base import AnalysisPipeline
from paper_analysis.runtime.pipelines.profiles import RESEARCH_PAPER_PROFILE


class ResearchPaperPipeline(AnalysisPipeline):
    def __init__(self, *, crew_runner: TextAnalysisCrewRunner | None = None) -> None:
        self._pipeline = GeneralTextPipeline(
            profile=RESEARCH_PAPER_PROFILE,
            crew_runner=crew_runner,
        )

    async def run(self, document: ParsedDocument) -> AnalysisResult:
        focused_document, selected_sections = self._build_focus_document(document)
        result = await self._pipeline.run(focused_document)
        result.structured_data = self._merge_parser_metadata(
            structured_data=result.structured_data,
            source_document=document,
        )
        result.structured_data = {
            **result.structured_data,
            "selected_sections": selected_sections,
            "source_structure": {
                "parser_kind": document.metadata.get("parser_kind", "unknown"),
                "page_count": document.metadata.get("page_count"),
                "doi": document.metadata.get("doi", ""),
                "section_order": document.section_order,
            },
        }
        result.markdown_report = self._build_report(
            source_document=document,
            result=result,
            selected_sections=selected_sections,
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
            metadata={**document.metadata, "selected_sections": selected_sections},
        )
        return focused_document, selected_sections

    def _build_report(
        self,
        *,
        source_document: ParsedDocument,
        result: AnalysisResult,
        selected_sections: list[str],
    ) -> str:
        paper_analysis = self._coerce_paper_analysis(result)
        source_section_preview = self._render_source_section_preview(source_document, selected_sections)
        selected_text = "\n".join(
            f"- {section.replace('_', ' ').title()}" for section in selected_sections
        ) or "- Fallback raw text"
        parser_authors = source_document.metadata.get("authors", [])
        if isinstance(parser_authors, list):
            fallback_authors = parser_authors
        else:
            fallback_authors = [str(parser_authors)] if parser_authors else []
        authors = ", ".join(paper_analysis.metadata.authors or fallback_authors) or "N/A"
        strengths = "\n".join(f"- {item}" for item in paper_analysis.strengths) or "- N/A"
        limitations = "\n".join(f"- {item}" for item in paper_analysis.limitations) or "- N/A"
        datasets = ", ".join(paper_analysis.extracted_notes.datasets) or "N/A"

        return f"""# Research Paper Analysis Report

## Source Document
- **Title:** {paper_analysis.metadata.title or source_document.title or 'N/A'}
- **Authors:** {authors}
- **DOI:** {source_document.metadata.get('doi') or 'N/A'}
- **Venue:** {paper_analysis.metadata.venue or source_document.metadata.get('venue') or 'N/A'}
- **Year:** {paper_analysis.metadata.year or source_document.metadata.get('year') or 'N/A'}
- **Pages:** {source_document.metadata.get('page_count') or 'N/A'}

## Selected Sections Used For Analysis
{selected_text}

## Structured Parse Preview
{source_section_preview}

## Research Problem
{paper_analysis.extracted_notes.research_problem or 'N/A'}

## Core Method
{paper_analysis.extracted_notes.core_method or 'N/A'}

## Datasets
{datasets}

## Experimental Setup
{paper_analysis.extracted_notes.experimental_setup or 'N/A'}

## Main Results
{paper_analysis.extracted_notes.main_results or 'N/A'}

## Novelty
{paper_analysis.novelty or 'N/A'}

## Strengths
{strengths}

## Limitations
{limitations}

## Reproducibility
{paper_analysis.reproducibility or 'N/A'}

## Summary
{result.summary or 'N/A'}

## Interview Pitch
{paper_analysis.interview_pitch or result.summary or 'N/A'}
"""

    @staticmethod
    def _render_source_section_preview(
        source_document: ParsedDocument,
        selected_sections: list[str],
    ) -> str:
        if not selected_sections:
            return "N/A"

        blocks: list[str] = []
        for section_name in selected_sections:
            content = source_document.sections.get(section_name, "").strip()
            if not content:
                continue
            preview = content[:700].strip()
            heading = section_name.replace("_", " ").title()
            blocks.append(f"### {heading}\n{preview}")
        return "\n\n".join(blocks) if blocks else "N/A"

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
                "interview_pitch",
            }
        }
        try:
            return PaperAnalysis.model_validate(payload)
        except ValidationError:
            return PaperAnalysis()

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
