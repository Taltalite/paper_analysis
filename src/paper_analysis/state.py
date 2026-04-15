from typing import Any

from pydantic import BaseModel, Field

from paper_analysis.domain.enums import AnalysisMode
from paper_analysis.domain.models import PaperAnalysis as PaperAnalysisOutput
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument


class PaperAnalysisState(BaseModel):
    input_path: str = "input/sample_paper.txt"
    mode: AnalysisMode = AnalysisMode.RESEARCH_PAPER
    paper_title_hint: str = ""
    raw_text: str = ""
    parsed_document: ParsedDocument | None = None

    analysis: AnalysisResult | None = None
    legacy_paper_analysis: PaperAnalysisOutput | None = None

    markdown_report: str = ""
    json_report: dict[str, Any] = Field(default_factory=dict)

    output_markdown_path: str = "output/report.md"
    output_json_path: str = "output/report.json"

    status: str = "initialized"
    error_message: str | None = None
