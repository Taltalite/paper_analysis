from enum import Enum


class DocumentKind(str, Enum):
    PLAIN_TEXT = "plain_text"
    PDF = "pdf"


class AnalysisMode(str, Enum):
    GENERAL_TEXT = "general_text"
    RESEARCH_PAPER = "research_paper"


class JobStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
