"""Linux 本地进程共享缓存：内容寻址、文件锁、原子写入、按需页面渲染。"""
from __future__ import annotations

import asyncio
import hashlib
import json
import fcntl
from pathlib import Path

from paper_analysis.adapters.parser.base import DocumentParser
from paper_analysis.adapters.parser.figure_semantics_base import FigureSemanticExtractor
from paper_analysis.adapters.storage.qa_store import atomic_json
from paper_analysis.domain.models import FigureMetadata, FigureSemanticArtifactBatch
from paper_analysis.domain.schemas import ParsedDocument


def parser_version() -> str:
    import fitz
    code = Path(__file__).with_name("pdf.py").read_bytes()
    return hashlib.sha256(code + fitz.VersionBind.encode() + b"qa-cache-v2").hexdigest()[:16]


class ParsedDocumentCache:
    def __init__(self, root: Path, parser: DocumentParser) -> None:
        self.root, self.parser = root.resolve(), parser
        self.version = parser_version()

    def get(self, source: Path) -> tuple[ParsedDocument, bool]:
        content = source.read_bytes()
        fingerprint = hashlib.sha256(content).hexdigest()
        directory = self.root / fingerprint / self.version
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "parse.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            parsed = directory / "parsed.json"
            cached_source = directory / "source.pdf"
            if parsed.exists() and cached_source.exists() and hashlib.sha256(cached_source.read_bytes()).hexdigest() == fingerprint:
                try:
                    manifest = json.loads((directory / "manifest.json").read_text())
                    if hashlib.sha256(parsed.read_bytes()).hexdigest() == manifest["parsed_sha256"]:
                        document = ParsedDocument.model_validate_json(parsed.read_text())
                        if document.metadata.get("document_sha256") == fingerprint:
                            return document, True
                except (ValueError, KeyError, OSError):
                    pass
            cached_source.write_bytes(content)
            document = asyncio.run(self.parser.parse(cached_source))
            document.metadata.update(document_sha256=fingerprint, source_path=str(cached_source), parser_version=self.version)
            atomic_json(parsed, document)
            atomic_json(directory / "manifest.json", {"parsed_sha256": hashlib.sha256(parsed.read_bytes()).hexdigest()})
            return document, False


def render_page(source: Path, page_number: int, *, highlight: list[float] | None = None) -> Path:
    import fitz
    suffix = hashlib.sha256(str(highlight).encode()).hexdigest()[:12] if highlight else "plain"
    directory = source.parent / ".paper_analysis_assets" / source.stem / "pages"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (f"page_{page_number}.png" if not highlight else f"page_{page_number}_{suffix}.png")
    with (directory / f"page_{page_number}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            document = fitz.open(source)
        except (RuntimeError, ValueError) as exc:
            raise ValueError("无法读取 PDF 页面，文件可能损坏或加密。") from exc
        with document:
            if not 1 <= page_number <= document.page_count:
                raise ValueError("PDF 页码超出范围。")
            if target.exists():
                return target
            page = document[page_number - 1]
            if highlight and len(highlight) == 4:
                page.draw_rect(fitz.Rect(*highlight), color=(1, 0.2, 0), fill=(1, 1, 0), fill_opacity=0.15, width=2)
            temporary = target.with_suffix(".tmp.png")
            page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(temporary)
            temporary.replace(target)
    return target


class OnDemandFigureExtractor:
    def __init__(self, delegate: FigureSemanticExtractor) -> None:
        self.delegate = delegate

    def extract(self, *, document: ParsedDocument, figures: list[FigureMetadata]) -> FigureSemanticArtifactBatch:
        import re
        source = Path(document.metadata["source_path"])
        for figure in figures:
            if figure.page_number:
                figure.page_snapshot_path = str(render_page(source, figure.page_number))
            pages = [int(match[1]) for path in figure.context_page_snapshot_paths
                     if (match := re.search(r"page_(\d+)\.png$", path))]
            figure.context_page_snapshot_paths = [str(render_page(source, page)) for page in pages]
        return self.delegate.extract(document=document, figures=figures)
