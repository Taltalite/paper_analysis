from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from paper_analysis.domain.schemas import ParsedDocument


class DocumentParser(ABC):
    @abstractmethod
    async def parse(self, path: Path) -> ParsedDocument:
        raise NotImplementedError
