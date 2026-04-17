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
    figure_analyses: list["FigureAnalysis"] = Field(default_factory=list)


class FigureMetadata(BaseModel):
    figure_id: str = ""
    caption: str = ""
    page_number: int | None = None
    page_snapshot_path: str | None = None
    referenced_text_spans: list[str] = Field(default_factory=list)
    caption_block_ids: list[str] = Field(default_factory=list)
    reference_block_ids: list[str] = Field(default_factory=list)


class DocumentBlock(BaseModel):
    block_id: str = ""
    page_number: int = 0
    order_index: int = 0
    block_type: str = "text"
    text: str = ""
    bbox: list[float] = Field(default_factory=list)
    max_size: float = 0.0
    image_path: str | None = None


class DocumentStructureDraft(BaseModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    doi: str = ""
    venue: str = ""
    year: str = ""
    abstract: str = ""
    sections: dict[str, str] = Field(default_factory=dict)
    section_order: list[str] = Field(default_factory=list)
    figures: list[FigureMetadata] = Field(default_factory=list)
    discarded_noise: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class FigureAnalysis(BaseModel):
    figure_id: str = ""
    figure_title_or_caption: str = ""
    experiment_focus: str = ""
    compared_items: list[str] = Field(default_factory=list)
    metrics_or_axes: list[str] = Field(default_factory=list)
    main_observations: list[str] = Field(default_factory=list)
    claimed_conclusion: str = ""
    consistency_check: str = ""
    confidence: str = "不足以判断"


class FigureAnalysisBatch(BaseModel):
    analyses: list[FigureAnalysis] = Field(default_factory=list)


class TextAnalysisSections(BaseModel):
    sections: dict[str, str | list[str]] = Field(default_factory=dict)


PaperAnalysis.model_rebuild()
FigureAnalysisBatch.model_rebuild()
DocumentStructureDraft.model_rebuild()
