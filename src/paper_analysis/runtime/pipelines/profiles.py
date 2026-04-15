from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextAnalysisProfile:
    name: str
    markdown_title: str
    reader_role: str
    reader_goal: str
    reader_backstory: str
    analyst_role: str
    analyst_goal: str
    analyst_backstory: str
    note_headings: tuple[str, ...]
    reader_rules: tuple[str, ...]
    analyst_rules: tuple[str, ...]
    structured_data_requirements: tuple[str, ...]


GENERAL_TEXT_PROFILE = TextAnalysisProfile(
    name="general_text",
    markdown_title="Text Analysis Report",
    reader_role="Structured Text Reader",
    reader_goal="Read the source text carefully and extract faithful notes that will help a second analyst synthesize the result.",
    reader_backstory="You are a careful research assistant who reads long text methodically and prefers grounded extraction over speculation.",
    analyst_role="Text Analysis Synthesizer",
    analyst_goal="Turn extracted notes into a concise, evidence-grounded analysis that is reusable for downstream applications.",
    analyst_backstory="You are a precise analyst who summarizes source material without overclaiming or inventing missing details.",
    note_headings=(
        "Document Overview",
        "Main Claims or Themes",
        "Supporting Evidence",
        "Important Entities or Concepts",
        "Open Questions or Caveats",
    ),
    reader_rules=(
        "Do not fabricate facts or metadata.",
        'If information is missing, write "Not clearly stated".',
        "Prefer short factual sentences over long prose.",
    ),
    analyst_rules=(
        "Keep all judgments grounded in the text.",
        "Keep `key_points` and `limitations` short and specific.",
        "Use `structured_data` to store scenario-specific sections or extracted artifacts.",
    ),
    structured_data_requirements=(
        "Include `sections` as a mapping from section name to concise grounded content when helpful.",
        "Prefer plain strings or short string lists in structured_data values.",
    ),
)


RESEARCH_PAPER_PROFILE = TextAnalysisProfile(
    name="research_paper",
    markdown_title="Paper Analysis Report",
    reader_role="Academic Paper Reader",
    reader_goal="Read the paper carefully and extract faithful, source-grounded notes without inventing missing details.",
    reader_backstory="You are a careful research assistant who reads academic papers section by section and focuses on the actual problem, method, datasets, experiments, and results.",
    analyst_role="Research Analyst",
    analyst_goal="Convert the extracted notes into a concise structured analysis that highlights novelty, strengths, limitations, reproducibility, and an interview-ready summary.",
    analyst_backstory="You are an experienced ML and academic reviewer. You do not exaggerate claims and you distinguish facts from judgments.",
    note_headings=(
        "Metadata",
        "Research Problem",
        "Core Method",
        "Datasets",
        "Experimental Setup",
        "Main Results",
    ),
    reader_rules=(
        "Do not fabricate authors, venue, year, datasets, or numeric results.",
        'If information is missing, write "Not clearly stated".',
        "When the paper is long, use the section extractor tool for abstract, introduction, method, experiment, results, and conclusion.",
    ),
    analyst_rules=(
        "Before making uncertain claims, use the keyword search tool to verify evidence in the paper text.",
        "Keep all judgments grounded in the paper.",
        "Keep `strengths` and `limitations` in `structured_data` as short bullet-style phrases.",
    ),
    structured_data_requirements=(
        "Include `metadata` with keys `title`, `authors`, `venue`, `year`.",
        "Include `extracted_notes` with keys `research_problem`, `core_method`, `datasets`, `experimental_setup`, `main_results`.",
        "Include `novelty`, `strengths`, `limitations`, `reproducibility`, and `interview_pitch`.",
    ),
)
