from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PaperMetadata(BaseModel):
    title: str = ""
    authors: List[str] = Field(default_factory=list)
    venue: str = ""
    year: str = ""


class ExtractedNotes(BaseModel):
    research_problem: str = ""
    core_method: str = ""
    datasets: List[str] = Field(default_factory=list)
    experimental_setup: str = ""
    main_results: str = ""


class PaperAnalysisOutput(BaseModel):
    metadata: PaperMetadata = Field(default_factory=PaperMetadata)
    extracted_notes: ExtractedNotes = Field(default_factory=ExtractedNotes)
    novelty: str = ""
    strengths: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    reproducibility: str = ""
    interview_pitch: str = ""


class PaperAnalysisState(BaseModel):
    input_path: str = "input/sample_paper.txt"
    paper_title_hint: str = ""
    raw_text: str = ""

    analysis: Optional[PaperAnalysisOutput] = None

    markdown_report: str = ""
    json_report: Dict[str, Any] = Field(default_factory=dict)

    output_markdown_path: str = "output/report.md"
    output_json_path: str = "output/report.json"

    status: str = "initialized"
    error_message: Optional[str] = None