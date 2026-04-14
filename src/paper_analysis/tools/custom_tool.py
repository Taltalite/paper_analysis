import re
from typing import List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class PaperSectionExtractorInput(BaseModel):
    paper_text: str = Field(..., description="Full plain-text content of the paper.")
    section_name: str = Field(
        ...,
        description="Requested section name, such as abstract, introduction, method, experiment, results, conclusion.",
    )


class PaperSectionExtractorTool(BaseTool):
    name: str = "paper_section_extractor"
    description: str = (
        "Extract a likely section from a plain-text academic paper by section name. "
        "Useful when the paper is long and you want to focus on abstract, methods, results, or conclusion."
    )
    args_schema: Type[BaseModel] = PaperSectionExtractorInput

    def _run(self, paper_text: str, section_name: str) -> str:
        text = paper_text.replace("\r\n", "\n").replace("\r", "\n")
        lines = text.split("\n")

        target = section_name.strip().lower()
        heading_aliases = {
            "abstract": ["abstract"],
            "introduction": ["introduction", "background"],
            "method": ["method", "methods", "materials and methods", "methodology"],
            "experiment": ["experiment", "experiments", "experimental setup", "evaluation"],
            "results": ["results", "findings"],
            "discussion": ["discussion"],
            "conclusion": ["conclusion", "conclusions", "summary"],
        }

        possible = heading_aliases.get(target, [target])

        def normalize_heading(line: str) -> str:
            line = line.strip().lower()
            line = re.sub(r"^[0-9ivx]+\s*[\.\)]\s*", "", line)
            line = re.sub(r"[:\-]+$", "", line)
            return line

        heading_positions = []
        for idx, line in enumerate(lines):
            norm = normalize_heading(line)
            if any(norm == p for p in sum(heading_aliases.values(), [])):
                heading_positions.append((idx, norm))

        for i, (start_idx, norm) in enumerate(heading_positions):
            if norm in possible:
                end_idx = heading_positions[i + 1][0] if i + 1 < len(heading_positions) else len(lines)
                chunk = "\n".join(lines[start_idx:end_idx]).strip()
                if chunk:
                    return chunk[:4000]

        if target == "abstract":
            return text[:2500].strip()

        return f"No clear section named '{section_name}' was found."
    

class PaperKeywordSearchInput(BaseModel):
    paper_text: str = Field(..., description="Full plain-text content of the paper.")
    keyword: str = Field(..., description="Keyword or phrase to search for.")
    max_hits: int = Field(default=5, description="Maximum number of snippets to return.")
    window_chars: int = Field(default=220, description="Number of surrounding characters to include around each hit.")


class PaperKeywordSearchTool(BaseTool):
    name: str = "paper_keyword_search"
    description: str = (
        "Search the full paper text for a keyword or phrase and return short supporting snippets. "
        "Useful for verifying claims about datasets, metrics, ablations, limitations, or conclusions."
    )
    args_schema: Type[BaseModel] = PaperKeywordSearchInput

    def _run(self, paper_text: str, keyword: str, max_hits: int = 5, window_chars: int = 220) -> str:
        text = paper_text.replace("\r\n", "\n").replace("\r", "\n")
        low_text = text.lower()
        low_key = keyword.lower().strip()

        if not low_key:
            return "Keyword is empty."

        hits: List[str] = []
        start = 0

        while len(hits) < max_hits:
            idx = low_text.find(low_key, start)
            if idx == -1:
                break

            left = max(0, idx - window_chars)
            right = min(len(text), idx + len(keyword) + window_chars)
            snippet = text[left:right].strip().replace("\n", " ")
            hits.append(f"[Hit {len(hits)+1}] ...{snippet}...")
            start = idx + len(low_key)

        if not hits:
            return f"No match found for keyword: {keyword}"

        return "\n".join(hits)