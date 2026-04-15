from __future__ import annotations

from pathlib import Path

from paper_analysis.adapters.parser.base import DocumentParser
from paper_analysis.domain.schemas import ParsedDocument


class PlainTextParser(DocumentParser):
    async def parse(self, path: Path) -> ParsedDocument:
        raw_text = path.read_text(encoding="utf-8").strip()
        title = self._infer_title(raw_text)
        return ParsedDocument(
            title=title,
            raw_text=raw_text,
            markdown=raw_text,
            metadata={"parser_kind": "plain_text"},
        )

    @staticmethod
    def _infer_title(raw_text: str) -> str:
        for line in raw_text.splitlines():
            clean = line.strip()
            if clean:
                return clean[:200]
        return ""
