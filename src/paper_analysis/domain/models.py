from pydantic import BaseModel, Field


class PaperMetadata(BaseModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    venue: str = ""
    year: str = ""


class ExtractedNotes(BaseModel):
    research_problem: str = ""
    core_method: str = ""
    datasets: list[str] = Field(default_factory=list)
    experimental_setup: str = ""
    main_results: str = ""


class PaperAnalysis(BaseModel):
    metadata: PaperMetadata = Field(default_factory=PaperMetadata)
    extracted_notes: ExtractedNotes = Field(default_factory=ExtractedNotes)
    novelty: str = ""
    strengths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reproducibility: str = ""
    interview_pitch: str = ""


class TextAnalysisSections(BaseModel):
    sections: dict[str, str | list[str]] = Field(default_factory=dict)
