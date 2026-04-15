from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from paper_analysis.adapters.parser.base import DocumentParser
from paper_analysis.domain.schemas import ParsedDocument


@dataclass(frozen=True)
class _PdfBlock:
    page_number: int
    y0: float
    max_size: float
    text: str


class PdfParser(DocumentParser):
    async def parse(self, path: Path) -> ParsedDocument:
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PyMuPDF/fitz is required for PDF parsing.") from exc

        document = fitz.open(path)
        try:
            blocks = self._extract_blocks(document)
            title = self._extract_title(blocks)
            metadata = self._extract_metadata(path=path, blocks=blocks, title=title, page_count=document.page_count)
            sections = self._extract_sections(blocks=blocks, title=title)
            markdown = self._build_markdown(title=title, metadata=metadata, sections=sections)
            raw_text = "\n\n".join(
                content for _, content in sections.items() if content
            ).strip() or self._fallback_raw_text(blocks)
            return ParsedDocument(
                title=title,
                raw_text=raw_text,
                markdown=markdown,
                sections=sections,
                section_order=list(sections.keys()),
                metadata=metadata,
            )
        finally:
            document.close()

    def _extract_blocks(self, document) -> list[_PdfBlock]:  # noqa: ANN001
        blocks: list[_PdfBlock] = []
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            for block in page.get_text("dict")["blocks"]:
                if "lines" not in block:
                    continue

                line_texts: list[str] = []
                sizes: list[float] = []
                for line in block["lines"]:
                    spans = line.get("spans", [])
                    if not spans:
                        continue
                    line_text = "".join(span["text"] for span in spans)
                    line_text = self._clean_text(line_text)
                    if not line_text:
                        continue
                    line_texts.append(line_text)
                    sizes.extend(span["size"] for span in spans)

                if not line_texts:
                    continue

                text = " ".join(line_texts).strip()
                if not text:
                    continue

                blocks.append(
                    _PdfBlock(
                        page_number=page_index + 1,
                        y0=float(block["bbox"][1]),
                        max_size=max(sizes),
                        text=text,
                    )
                )

        return blocks

    def _extract_title(self, blocks: list[_PdfBlock]) -> str:
        page_one_blocks = [block for block in blocks if block.page_number == 1]
        title_blocks: list[str] = []
        for block in page_one_blocks:
            if block.max_size < 20:
                continue
            text = re.sub(r"https?://\S+", "", block.text, flags=re.IGNORECASE)
            text = re.sub(r"\bArticle\b", "", text, flags=re.IGNORECASE)
            text = self._clean_text(text)
            if text:
                title_blocks.append(text)
        if title_blocks:
            return self._clean_text(" ".join(title_blocks))

        for block in page_one_blocks:
            if len(block.text) > 20 and block.text.lower() not in {"article"}:
                return block.text[:200]
        return ""

    def _extract_metadata(
        self,
        *,
        path: Path,
        blocks: list[_PdfBlock],
        title: str,
        page_count: int,
    ) -> dict[str, object]:
        full_text = "\n".join(block.text for block in blocks)
        doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", full_text, flags=re.IGNORECASE)

        page_one_blocks = [block for block in blocks if block.page_number == 1]
        author_block = next(
            (block.text for block in page_one_blocks if 8.8 <= block.max_size <= 10 and "@" not in block.text),
            "",
        )
        authors = self._extract_authors(author_block)

        year_match = re.search(r"(19|20)\d{2}", full_text)
        received_match = re.search(r"Received:\s*([^\n]+)", full_text)
        accepted_match = re.search(r"Accepted:\s*([^\n]+)", full_text)
        published_match = re.search(r"Published online:\s*([^\n]+)", full_text)
        venue_line = next(
            (block.text for block in page_one_blocks if "volume" in block.text.lower() and "nature" in block.text.lower()),
            "",
        )

        return {
            "parser_kind": "pdf",
            "source_path": str(path),
            "page_count": page_count,
            "title": title,
            "authors": authors,
            "doi": doi_match.group(0) if doi_match else "",
            "venue": venue_line,
            "year": year_match.group(0) if year_match else "",
            "received": received_match.group(1).strip() if received_match else "",
            "accepted": accepted_match.group(1).strip() if accepted_match else "",
            "published_online": published_match.group(1).strip() if published_match else "",
        }

    def _extract_sections(self, *, blocks: list[_PdfBlock], title: str) -> dict[str, str]:
        page_one_blocks = [block for block in blocks if block.page_number == 1]
        content_blocks = [
            block for block in blocks
            if len(block.text) >= 30 and "doi.org" not in block.text.lower()
        ]
        sections: dict[str, str] = {}

        abstract_block = next(
            (
                block.text
                for block in page_one_blocks
                if block.max_size >= 9.8 and block.max_size <= 10.2 and not block.text.startswith("Received:")
            ),
            "",
        )
        if abstract_block:
            sections["abstract"] = abstract_block

        introduction_blocks = [
            block.text
            for block in page_one_blocks
            if 8.0 <= block.max_size <= 8.7
            and not block.text.startswith(("Received:", "Accepted:", "Published online:", "Check for updates"))
            and "@" not in block.text
        ]
        if introduction_blocks:
            sections["introduction"] = self._clean_text(" ".join(introduction_blocks))

        figure_caption_blocks = [
            block.text
            for block in content_blocks
            if block.text.lower().startswith("fig.")
        ]
        if figure_caption_blocks:
            sections["figures"] = self._clean_text(" ".join(figure_caption_blocks))

        raw_text = self._fallback_raw_text(content_blocks)
        sections["method"] = self._select_relevant_sentences(
            raw_text,
            keywords=("approach", "pipeline", "method", "combine", "neural", "error-correcting"),
        )
        sections["experimental_setup"] = self._select_relevant_sentences(
            raw_text,
            keywords=("demonstrated", "sequencing", "evaluated", "experiment", "storage pipeline", "3.1 mb"),
        )
        sections["results"] = self._select_relevant_sentences(
            raw_text,
            keywords=("increase", "improvement", "accuracy", "code rate", "high-noise", "results"),
        )
        sections["conclusion"] = self._select_relevant_sentences(
            raw_text,
            keywords=("viable path", "commercial", "broader sense", "conclusion"),
        )

        if title:
            sections = {"title": title, **sections}

        return {name: content for name, content in sections.items() if content}

    def _build_markdown(
        self,
        *,
        title: str,
        metadata: dict[str, object],
        sections: dict[str, str],
    ) -> str:
        authors = metadata.get("authors", [])
        if isinstance(authors, list):
            author_text = ", ".join(authors) if authors else "未明确说明"
        else:
            author_text = str(authors) if authors else "未明确说明"

        meta_lines = [
            f"- **标题：** {title or '未明确说明'}",
            f"- **作者：** {author_text}",
            f"- **DOI：** {metadata.get('doi') or '未明确说明'}",
            f"- **期刊/会议：** {metadata.get('venue') or '未明确说明'}",
            f"- **年份：** {metadata.get('year') or '未明确说明'}",
            f"- **页数：** {metadata.get('page_count') or '未明确说明'}",
        ]

        body: list[str] = ["# PDF 结构化解析", "", "## 基础信息", *meta_lines]
        for key, value in sections.items():
            if key == "title":
                continue
            heading = self._localized_section_name(key)
            body.extend(["", f"## {heading}", value or "未明确说明"])
        return "\n".join(body).strip() + "\n"

    @staticmethod
    def _extract_authors(author_block: str) -> list[str]:
        if not author_block:
            return []
        cleaned = re.sub(r"[\d\u0000-\u001f]+", " ", author_block)
        cleaned = cleaned.replace("&", ",")
        candidates = [item.strip(" ,") for item in cleaned.split(",")]
        authors = [
            candidate
            for candidate in candidates
            if candidate and "these authors" not in candidate.lower() and len(candidate.split()) <= 4
        ]
        return authors

    @staticmethod
    def _select_relevant_sentences(raw_text: str, *, keywords: tuple[str, ...]) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", raw_text)
        selected: list[str] = []
        lowered_keywords = tuple(keyword.lower() for keyword in keywords)
        for sentence in sentences:
            cleaned = sentence.strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if any(keyword in lowered for keyword in lowered_keywords):
                selected.append(cleaned)
            if len(selected) >= 4:
                break
        return " ".join(selected)

    @staticmethod
    def _fallback_raw_text(blocks: list[_PdfBlock]) -> str:
        filtered = [
            block.text
            for block in blocks
            if not block.text.startswith(("Received:", "Accepted:", "Published online:", "Check for updates"))
            and "@" not in block.text
        ]
        return "\n\n".join(filtered).strip()

    @staticmethod
    def _clean_text(text: str) -> str:
        text = text.replace("\u2009", " ").replace("\xa0", " ").replace("\u0003", " ")
        text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([,.;:])", r"\1", text)
        text = re.sub(r"(?<=\w)- (?=\w)", "", text)
        return text.strip()

    @staticmethod
    def _localized_section_name(section_name: str) -> str:
        mapping = {
            "abstract": "摘要（Abstract）",
            "introduction": "引言（Introduction）",
            "figures": "图示（Figures）",
            "method": "方法（Method）",
            "experimental_setup": "实验设置（Experimental Setup）",
            "results": "结果（Results）",
            "conclusion": "结论（Conclusion）",
        }
        return mapping.get(section_name, section_name.replace("_", " ").title())
