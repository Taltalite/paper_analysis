"""参考证据的 PDF 定位接口；不调用任何语言或视觉模型。"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class PdfSourceInspector(Protocol):
    def page_count(self, path: Path) -> int: ...

    def region_text(self, path: Path, page_1_based: int,
                    bbox: list[float] | None = None) -> str: ...


class PyMuPdfSourceInspector:
    def page_count(self, path: Path) -> int:
        import fitz

        with fitz.open(path) as document:
            return len(document)

    def region_text(self, path: Path, page_1_based: int,
                    bbox: list[float] | None = None) -> str:
        import fitz

        with fitz.open(path) as document:
            if not 1 <= page_1_based <= len(document):
                raise ValueError("证据页码越界。")
            page = document[page_1_based - 1]
            area = fitz.Rect(*bbox) if bbox else None
            if area is not None and not page.rect.contains(area):
                raise ValueError("证据坐标越界。")
            return page.get_text(clip=area)
