from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from paper_analysis.adapters.parser.base import DocumentParser
from paper_analysis.domain.models import DocumentBlock, DocumentStructureDraft, FigureMetadata
from paper_analysis.domain.schemas import ParsedDocument


@dataclass(frozen=True)
class _PdfBlock:
    block_id: str
    page_number: int
    order_index: int
    y0: float
    max_size: float
    bbox: tuple[float, float, float, float]
    block_type: str
    text: str = ""
    image_path: str | None = None


class PdfParser(DocumentParser):
    _SECTION_ALIASES = {
        "abstract": "abstract",
        "introduction": "introduction",
        "background": "introduction",
        "results": "results",
        "discussion": "discussion",
        "results and discussion": "results",
        "methods": "method",
        "method": "method",
        "materials and methods": "method",
        "experimental procedures": "experimental_setup",
        "experimental setup": "experimental_setup",
        "experimental section": "experimental_setup",
        "conclusion": "conclusion",
        "conclusions": "conclusion",
    }

    _NOISE_PATTERNS = (
        r"^downloaded from https?://",
        r"^view the article online",
        r"^copyright",
        r"^open access",
        r"^this article is distributed",
        r"^supplementary materials",
        r"^article type",
        r"^\d+\s*$",
        r"^page \d+",
        r"^received\b",
        r"^accepted\b",
        r"^published\b",
    )

    async def parse(self, path: Path) -> ParsedDocument:
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PyMuPDF/fitz is required for PDF parsing.") from exc

        document = fitz.open(path)
        try:
            blocks = self._extract_blocks(document=document, path=path)
            title, title_block_ids = self._extract_title(blocks)
            figures = self._extract_figures(document=document, path=path, blocks=blocks)
            metadata = self._extract_metadata(
                path=path,
                blocks=blocks,
                title=title,
                page_count=document.page_count,
                title_block_ids=title_block_ids,
            )
            coarse_structure = self._build_coarse_structure(
                blocks=blocks,
                title=title,
                title_block_ids=title_block_ids,
                metadata=metadata,
                figures=figures,
            )

            final_title = coarse_structure.title or title
            final_authors = coarse_structure.authors or self._list_value(metadata.get("authors"))
            final_doi = coarse_structure.doi or self._string_value(metadata.get("doi"))
            final_venue = coarse_structure.venue or self._string_value(metadata.get("venue"))
            final_year = coarse_structure.year or self._string_value(metadata.get("year"))
            final_figures = coarse_structure.figures or figures
            sections = self._sections_from_draft(coarse_structure=coarse_structure, title=final_title)
            markdown = self._build_markdown(
                title=final_title,
                metadata={
                    **metadata,
                    "title": final_title,
                    "authors": final_authors,
                    "doi": final_doi,
                    "venue": final_venue,
                    "year": final_year,
                    "figure_count": len(final_figures),
                },
                sections=sections,
                figures=final_figures,
            )
            raw_text = self._build_raw_text(sections=sections, fallback_blocks=blocks)
            ordered_blocks = [self._to_document_block(block).model_dump(mode="json") for block in blocks]

            return ParsedDocument(
                title=final_title,
                raw_text=raw_text,
                markdown=markdown,
                sections=sections,
                section_order=list(sections.keys()),
                figures=final_figures,
                metadata={
                    **metadata,
                    "title": final_title,
                    "authors": final_authors,
                    "doi": final_doi,
                    "venue": final_venue,
                    "year": final_year,
                    "figure_count": len(final_figures),
                    "ordered_blocks": ordered_blocks,
                    "coarse_structure": coarse_structure.model_dump(mode="json"),
                },
            )
        finally:
            document.close()

    def _extract_blocks(self, *, document, path: Path) -> list[_PdfBlock]:  # noqa: ANN001
        blocks: list[_PdfBlock] = []
        order_index = 0
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            for raw_index, raw_block in enumerate(page.get_text("dict")["blocks"]):
                bbox = tuple(float(value) for value in raw_block["bbox"])
                block_id = f"p{page_index + 1}_b{raw_index}"
                if "lines" in raw_block:
                    line_texts: list[str] = []
                    sizes: list[float] = []
                    for line in raw_block["lines"]:
                        spans = line.get("spans", [])
                        if not spans:
                            continue
                        text = "".join(span.get("text", "") for span in spans)
                        text = self._clean_text(text)
                        if not text:
                            continue
                        line_texts.append(text)
                        sizes.extend(float(span.get("size", 0.0)) for span in spans)
                    if not line_texts:
                        continue
                    blocks.append(
                        _PdfBlock(
                            block_id=block_id,
                            page_number=page_index + 1,
                            order_index=order_index,
                            y0=bbox[1],
                            max_size=max(sizes) if sizes else 0.0,
                            bbox=bbox,
                            block_type="text",
                            text=" ".join(line_texts).strip(),
                        )
                    )
                    order_index += 1
                    continue

                if raw_block.get("type") == 1:
                    image_path = self._save_image_block(
                        document=document,
                        source_path=path,
                        page_number=page_index + 1,
                        block_id=block_id,
                        bbox=bbox,
                    )
                    if image_path is None:
                        continue
                    blocks.append(
                        _PdfBlock(
                            block_id=block_id,
                            page_number=page_index + 1,
                            order_index=order_index,
                            y0=bbox[1],
                            max_size=0.0,
                            bbox=bbox,
                            block_type="image",
                            image_path=image_path,
                        )
                    )
                    order_index += 1

        return blocks

    def _extract_title(self, blocks: list[_PdfBlock]) -> tuple[str, list[str]]:
        page_one_blocks = [
            block
            for block in blocks
            if block.page_number == 1
            and block.block_type == "text"
            and block.text
            and not self._is_noise_text(block.text)
            and not self._looks_like_citation_line(block.text)
            and not self._looks_like_venue_line(block.text)
            and not self._looks_like_author_line(block.text)
            and not self._detect_heading_key(block.text)
        ]
        if not page_one_blocks:
            return "", []

        top_blocks = [block for block in page_one_blocks if block.y0 < 220]
        candidates = top_blocks or page_one_blocks[:6]
        if not candidates:
            return "", []

        max_size = max(block.max_size for block in candidates)
        title_blocks = [
            block
            for block in candidates
            if block.max_size >= max(12.0, max_size - 1.2)
        ]
        if not title_blocks:
            title_blocks = sorted(candidates, key=lambda block: (-block.max_size, block.order_index))[:2]

        title_blocks = sorted(title_blocks, key=lambda block: block.order_index)[:2]
        cleaned_chunks = [
            self._clean_title_candidate(block.text)
            for block in title_blocks
        ]
        title = self._clean_text(" ".join(chunk for chunk in cleaned_chunks if chunk))
        return title, [block.block_id for block in title_blocks]

    def _extract_metadata(
        self,
        *,
        path: Path,
        blocks: list[_PdfBlock],
        title: str,
        page_count: int,
        title_block_ids: list[str],
    ) -> dict[str, object]:
        text_blocks = [block for block in blocks if block.block_type == "text" and block.text]
        page_one_blocks = [block for block in text_blocks if block.page_number == 1]
        title_ids = set(title_block_ids)
        doi = self._find_best_doi(text_blocks)
        venue = self._find_venue(page_one_blocks)
        year = self._find_year(page_one_blocks)
        authors = self._extract_authors_from_blocks(page_one_blocks, title_ids)

        return {
            "parser_kind": "pdf",
            "source_path": str(path),
            "page_count": page_count,
            "title": title,
            "authors": authors,
            "doi": doi,
            "venue": venue,
            "year": year,
        }

    def _build_coarse_structure(
        self,
        *,
        blocks: list[_PdfBlock],
        title: str,
        title_block_ids: list[str],
        metadata: dict[str, object],
        figures: list[FigureMetadata],
    ) -> DocumentStructureDraft:
        text_blocks = [block for block in blocks if block.block_type == "text" and block.text]
        title_id_set = set(title_block_ids)
        discarded_noise = [
            block.text
            for block in text_blocks
            if self._is_noise_text(block.text)
        ]
        heading_positions: list[tuple[str, int]] = []
        seen_headings: set[tuple[str, int]] = set()
        for index, block in enumerate(text_blocks):
            heading_key = self._detect_heading_key(block.text)
            if heading_key is None:
                continue
            marker = (heading_key, block.page_number)
            if marker in seen_headings:
                continue
            seen_headings.add(marker)
            heading_positions.append((heading_key, index))

        sections: dict[str, str] = {}
        section_order: list[str] = []
        caption_block_ids = {caption_id for figure in figures for caption_id in figure.caption_block_ids}
        for position, (heading_key, start_index) in enumerate(heading_positions):
            end_index = heading_positions[position + 1][1] if position + 1 < len(heading_positions) else len(text_blocks)
            chunks = [
                block.text
                for block in text_blocks[start_index + 1 : end_index]
                if block.block_id not in caption_block_ids
                and not self._is_noise_text(block.text)
                and not self._looks_like_citation_line(block.text)
                and not self._looks_like_author_line(block.text)
            ]
            content = self._clean_text(" ".join(chunks))
            if not content:
                continue
            sections[heading_key] = content
            section_order.append(heading_key)

        abstract = sections.get("abstract", "")
        if not abstract:
            abstract = self._fallback_abstract(text_blocks=text_blocks, title_block_ids=title_id_set)
            if abstract:
                sections["abstract"] = abstract
                section_order = ["abstract", *section_order]

        raw_text = self._fallback_raw_text(blocks)
        fallback_keywords = {
            "method": ("approach", "pipeline", "method", "combine", "neural", "error-correcting"),
            "experimental_setup": ("demonstrated", "sequencing", "evaluated", "experiment", "3.1 mb"),
            "results": ("increase", "improvement", "accuracy", "code rate", "high-noise", "results"),
            "conclusion": ("viable path", "commercial", "broader sense", "conclusion"),
        }
        for key, keywords in fallback_keywords.items():
            if key in sections:
                continue
            fallback = self._select_relevant_sentences(raw_text, keywords=keywords)
            if fallback:
                sections[key] = fallback
                section_order.append(key)

        return DocumentStructureDraft(
            title=title,
            authors=self._extract_authors_from_blocks(
                [block for block in text_blocks if block.page_number == 1],
                title_id_set,
            )
            or self._list_value(metadata.get("authors")),
            doi=self._string_value(metadata.get("doi")),
            venue=self._string_value(metadata.get("venue")),
            year=self._string_value(metadata.get("year")),
            abstract=abstract,
            sections=sections,
            section_order=self._dedupe_preserve_order(section_order),
            figures=figures,
            discarded_noise=discarded_noise[:20],
            uncertainties=self._build_uncertainties(title=title, sections=sections, figures=figures),
        )

    def _extract_figures(
        self,
        *,
        document,  # noqa: ANN001
        path: Path,
        blocks: list[_PdfBlock],
    ) -> list[FigureMetadata]:
        figures: list[FigureMetadata] = []
        text_blocks = [block for block in blocks if block.block_type == "text" and block.text]
        index = 0
        while index < len(text_blocks):
            block = text_blocks[index]
            figure_id = self._extract_figure_id(block.text)
            if figure_id is None:
                index += 1
                continue

            caption_blocks = [block]
            next_index = index + 1
            while next_index < len(text_blocks):
                candidate = text_blocks[next_index]
                if candidate.page_number != block.page_number:
                    break
                if self._extract_figure_id(candidate.text):
                    break
                if self._detect_heading_key(candidate.text):
                    break
                if self._is_noise_text(candidate.text):
                    next_index += 1
                    continue
                if candidate.y0 - caption_blocks[-1].y0 > 120:
                    break
                if len(candidate.text) < 12:
                    break
                caption_blocks.append(candidate)
                next_index += 1

            caption_text = self._clean_text(" ".join(item.text for item in caption_blocks))
            caption_block_ids = [item.block_id for item in caption_blocks]
            page_snapshot_path = self._save_page_snapshot(
                document=document,
                source_path=path,
                page_number=block.page_number,
            )
            reference_texts, reference_ids = self._extract_figure_references(
                blocks=text_blocks,
                figure_id=figure_id,
                caption_block_ids=set(caption_block_ids),
            )
            figures.append(
                FigureMetadata(
                    figure_id=figure_id,
                    caption=caption_text,
                    page_number=block.page_number,
                    page_snapshot_path=page_snapshot_path,
                    referenced_text_spans=reference_texts,
                    caption_block_ids=caption_block_ids,
                    reference_block_ids=reference_ids,
                )
            )
            index = next_index

        return figures

    def _extract_figure_references(
        self,
        *,
        blocks: list[_PdfBlock],
        figure_id: str,
        caption_block_ids: set[str],
    ) -> tuple[list[str], list[str]]:
        pattern = self._figure_reference_pattern(figure_id)
        references: list[str] = []
        reference_ids: list[str] = []
        for block in blocks:
            if block.block_id in caption_block_ids:
                continue
            if self._is_noise_text(block.text):
                continue
            if pattern.search(block.text):
                references.append(block.text)
                reference_ids.append(block.block_id)
            if len(references) >= 4:
                break
        if references:
            return references, reference_ids

        caption_indices = [
            index for index, block in enumerate(blocks) if block.block_id in caption_block_ids
        ]
        if not caption_indices:
            return references, reference_ids

        start_index = min(caption_indices)
        fallback_refs: list[str] = []
        fallback_ids: list[str] = []
        for offset in (-2, -1, 1, 2):
            candidate_index = start_index + offset
            if candidate_index < 0 or candidate_index >= len(blocks):
                continue
            candidate = blocks[candidate_index]
            if candidate.block_id in caption_block_ids:
                continue
            if self._is_noise_text(candidate.text):
                continue
            if candidate.block_type != "text" or len(candidate.text) < 40:
                continue
            fallback_refs.append(candidate.text)
            fallback_ids.append(candidate.block_id)
        return fallback_refs[:2], fallback_ids[:2]

    def _build_markdown(
        self,
        *,
        title: str,
        metadata: dict[str, object],
        sections: dict[str, str],
        figures: list[FigureMetadata],
    ) -> str:
        authors = self._list_value(metadata.get("authors"))
        author_text = ", ".join(authors) if authors else "未明确说明"
        meta_lines = [
            f"- **标题：** {title or '未明确说明'}",
            f"- **作者：** {author_text}",
            f"- **DOI：** {metadata.get('doi') or '未明确说明'}",
            f"- **期刊/会议：** {metadata.get('venue') or '未明确说明'}",
            f"- **年份：** {metadata.get('year') or '未明确说明'}",
            f"- **页数：** {metadata.get('page_count') or '未明确说明'}",
            f"- **图表数量：** {metadata.get('figure_count') or 0}",
        ]

        body: list[str] = ["# PDF 结构化解析", "", "## 基础信息", *meta_lines]
        if figures:
            body.extend(["", "## 图表元数据"])
            for figure in figures:
                refs = (
                    "\n".join(f"- {span}" for span in figure.referenced_text_spans)
                    if figure.referenced_text_spans
                    else "- 未明确说明"
                )
                body.extend(
                    [
                        "",
                        f"### {figure.figure_id or '未编号图表'}",
                        f"- **Caption：** {figure.caption or '未明确说明'}",
                        f"- **页码：** {figure.page_number if figure.page_number is not None else '未明确说明'}",
                        f"- **页截图路径：** {figure.page_snapshot_path or '未提供'}",
                        "- **正文引用：**",
                        refs,
                    ]
                )

        for key, value in sections.items():
            if key == "title" or key == "figures":
                continue
            body.extend(["", f"## {self._localized_section_name(key)}", value or "未明确说明"])
        return "\n".join(body).strip() + "\n"

    @staticmethod
    def _to_document_block(block: _PdfBlock) -> DocumentBlock:
        return DocumentBlock(
            block_id=block.block_id,
            page_number=block.page_number,
            order_index=block.order_index,
            block_type=block.block_type,
            text=block.text,
            bbox=list(block.bbox),
            max_size=block.max_size,
            image_path=block.image_path,
        )

    def _sections_from_draft(
        self,
        *,
        coarse_structure: DocumentStructureDraft,
        title: str,
    ) -> dict[str, str]:
        sections = {"title": title} if title else {}
        for key in coarse_structure.section_order:
            content = coarse_structure.sections.get(key, "")
            if content:
                sections[key] = content
        for key, value in coarse_structure.sections.items():
            if key not in sections and value:
                sections[key] = value
        if coarse_structure.figures:
            sections["figures"] = self._build_figure_section(coarse_structure.figures)
        return sections

    def _build_raw_text(self, *, sections: dict[str, str], fallback_blocks: list[_PdfBlock]) -> str:
        ordered_sections = [
            content
            for key, content in sections.items()
            if key not in {"title", "figures"} and content
        ]
        if ordered_sections:
            return "\n\n".join(ordered_sections).strip()
        return self._fallback_raw_text(fallback_blocks)

    def _find_best_doi(self, blocks: list[_PdfBlock]) -> str:
        candidates: list[tuple[int, str]] = []
        for block in blocks:
            if not block.text:
                continue
            for match in re.findall(r"10\.\d{4,9}/[A-Za-z0-9._;()/:+-]+", block.text, flags=re.IGNORECASE):
                cleaned = match.rstrip(").,;:")
                if cleaned.endswith("-"):
                    continue
                score = 0
                lowered = block.text.lower()
                if "doi" in lowered:
                    score += 4
                if "doi.org" in lowered:
                    score += 3
                if block.page_number <= 2:
                    score += 2
                if len(cleaned) >= 15:
                    score += 1
                candidates.append((score, cleaned))
        if not candidates:
            return ""
        candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
        return candidates[0][1]

    def _find_venue(self, page_one_blocks: list[_PdfBlock]) -> str:
        patterns = (
            r"\bSci\. Adv\.\b.*",
            r"\bScience Advances\b.*",
            r"\bNature\b.*",
            r"\bNature [A-Za-z ]+\b.*",
            r"\bCell\b.*",
            r"\barXiv\b.*",
        )
        for block in page_one_blocks:
            if self._is_noise_text(block.text):
                continue
            for pattern in patterns:
                match = re.search(pattern, block.text, flags=re.IGNORECASE)
                if match:
                    return self._clean_text(match.group(0))
        return ""

    def _find_year(self, page_one_blocks: list[_PdfBlock]) -> str:
        for block in page_one_blocks:
            if self._looks_like_citation_line(block.text) or "published" in block.text.lower():
                year_match = re.search(r"(19|20)\d{2}", block.text)
                if year_match:
                    return year_match.group(0)
        for block in page_one_blocks:
            year_match = re.search(r"(19|20)\d{2}", block.text)
            if year_match:
                return year_match.group(0)
        return ""

    def _extract_authors_from_blocks(
        self,
        blocks: list[_PdfBlock],
        title_block_ids: set[str],
    ) -> list[str]:
        author_candidates: list[str] = []
        passed_title = False
        for block in blocks:
            if block.block_id in title_block_ids:
                passed_title = True
                continue
            if not passed_title:
                continue
            if self._detect_heading_key(block.text):
                break
            if self._is_noise_text(block.text):
                continue
            if self._looks_like_author_line(block.text):
                author_candidates.append(block.text)
            if len(author_candidates) >= 3:
                break

        if not author_candidates:
            return []

        combined = " ".join(author_candidates)
        combined = re.sub(r"[*†‡§¶‖]+", " ", combined)
        combined = re.sub(r"\d+", " ", combined)
        combined = combined.replace("&", ",")
        name_matches = re.findall(
            r"[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){1,3}",
            combined,
        )
        return self._dedupe_preserve_order([self._clean_text(name) for name in name_matches if name])

    def _fallback_abstract(self, *, text_blocks: list[_PdfBlock], title_block_ids: set[str]) -> str:
        page_one_blocks = [block for block in text_blocks if block.page_number == 1]
        passed_title = False
        candidates: list[str] = []
        for block in page_one_blocks:
            if block.block_id in title_block_ids:
                passed_title = True
                continue
            if not passed_title:
                continue
            if self._is_noise_text(block.text) or self._looks_like_author_line(block.text):
                continue
            if self._looks_like_citation_line(block.text):
                continue
            if self._detect_heading_key(block.text):
                break
            if len(block.text) < 80:
                continue
            candidates.append(block.text)
            if len(candidates) >= 2:
                break
        return self._clean_text(" ".join(candidates))

    def _build_uncertainties(
        self,
        *,
        title: str,
        sections: dict[str, str],
        figures: list[FigureMetadata],
    ) -> list[str]:
        uncertainties: list[str] = []
        if not title:
            uncertainties.append("标题未能通过规则可靠识别。")
        for section in ("abstract", "introduction", "method", "results"):
            if section not in sections:
                uncertainties.append(f"未通过规则可靠识别章节：{section}。")
        if not figures:
            uncertainties.append("未通过规则可靠识别图表 caption。")
        return uncertainties

    @staticmethod
    def _build_figure_section(figures: list[FigureMetadata]) -> str:
        blocks: list[str] = []
        for figure in figures:
            refs = (
                "\n".join(f"- {item}" for item in figure.referenced_text_spans)
                if figure.referenced_text_spans
                else "- 未明确说明"
            )
            blocks.append(
                "\n".join(
                    [
                        f"### {figure.figure_id or '未编号图表'}",
                        figure.caption or "未明确说明",
                        "",
                        "正文引用：",
                        refs,
                    ]
                )
            )
        return "\n\n".join(blocks)

    @classmethod
    def _detect_heading_key(cls, text: str) -> str | None:
        normalized = cls._normalize_heading(text)
        return cls._SECTION_ALIASES.get(normalized)

    @staticmethod
    def _normalize_heading(text: str) -> str:
        normalized = re.sub(r"[^A-Za-z ]+", " ", text).strip().lower()
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def _is_noise_text(self, text: str) -> bool:
        lowered = text.strip().lower()
        for pattern in self._NOISE_PATTERNS:
            if re.search(pattern, lowered):
                return True
        return False

    @staticmethod
    def _looks_like_citation_line(text: str) -> bool:
        lowered = text.lower()
        return bool(
            re.search(r"\bet al\.,", lowered)
            or re.search(r"\bsci\. adv\.\b", lowered)
            or re.search(r"\bscience advances\b", lowered)
        )

    @staticmethod
    def _looks_like_venue_line(text: str) -> bool:
        lowered = text.lower()
        return bool(
            "volume" in lowered
            or "issue" in lowered
            or re.search(r"\bnature\b", lowered)
            or re.search(r"\bsci\. adv\.\b", lowered)
        )

    @staticmethod
    def _looks_like_author_line(text: str) -> bool:
        cleaned = re.sub(r"[*†‡§¶‖\d]+", " ", text)
        name_matches = re.findall(
            r"[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){1,3}",
            cleaned,
        )
        return len(name_matches) >= 2

    @staticmethod
    def _extract_figure_id(text: str) -> str | None:
        match = re.match(r"^\s*(fig(?:ure)?\.?\s*(\d+[A-Za-z]?))\b", text, flags=re.IGNORECASE)
        if not match:
            return None
        normalized = re.sub(r"\s+", " ", match.group(2).upper())
        return f"Figure {normalized}"

    @staticmethod
    def _figure_reference_pattern(figure_id: str) -> re.Pattern[str]:
        suffix = figure_id.removeprefix("Figure ").strip()
        return re.compile(rf"\b(?:fig(?:ure)?\.?)\s*{re.escape(suffix)}\b", flags=re.IGNORECASE)

    def _save_page_snapshot(
        self,
        *,
        document,  # noqa: ANN001
        source_path: Path,
        page_number: int,
    ) -> str | None:
        try:
            import fitz
        except ImportError:
            return None

        asset_dir = self._asset_dir(source_path) / "pages"
        asset_dir.mkdir(parents=True, exist_ok=True)
        target_path = asset_dir / f"page_{page_number}.png"
        if target_path.exists():
            return str(target_path)

        page = document.load_page(page_number - 1)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        pixmap.save(target_path)
        return str(target_path)

    def _save_image_block(
        self,
        *,
        document,  # noqa: ANN001
        source_path: Path,
        page_number: int,
        block_id: str,
        bbox: tuple[float, float, float, float],
    ) -> str | None:
        try:
            import fitz
        except ImportError:
            return None

        if bbox[2] - bbox[0] < 40 or bbox[3] - bbox[1] < 40:
            return None

        asset_dir = self._asset_dir(source_path) / "images"
        asset_dir.mkdir(parents=True, exist_ok=True)
        target_path = asset_dir / f"{block_id}.png"
        if target_path.exists():
            return str(target_path)

        page = document.load_page(page_number - 1)
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(1.5, 1.5),
            clip=fitz.Rect(*bbox),
            alpha=False,
        )
        pixmap.save(target_path)
        return str(target_path)

    @staticmethod
    def _asset_dir(source_path: Path) -> Path:
        return source_path.parent / ".paper_analysis_assets" / source_path.stem

    @staticmethod
    def _fallback_raw_text(blocks: list[_PdfBlock]) -> str:
        filtered = [
            block.text
            for block in blocks
            if block.block_type == "text" and block.text
        ]
        return "\n\n".join(filtered).strip()

    @staticmethod
    def _select_relevant_sentences(raw_text: str, *, keywords: tuple[str, ...]) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", raw_text)
        lowered_keywords = tuple(keyword.lower() for keyword in keywords)
        selected: list[str] = []
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
    def _clean_text(text: str) -> str:
        text = text.replace("\u2009", " ").replace("\xa0", " ").replace("\u0003", " ")
        text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([,.;:])", r"\1", text)
        text = re.sub(r"(?<=\w)- (?=\w)", "", text)
        return text.strip()

    @classmethod
    def _clean_title_candidate(cls, text: str) -> str:
        text = cls._clean_text(text)
        text = re.sub(r"https?://\S+", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bArticle\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bCheck for updates\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bdoi[: ]\S+", " ", text, flags=re.IGNORECASE)
        return cls._clean_text(text)

    @staticmethod
    def _string_value(value: object) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def _list_value(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).strip()
        return [text] if text else []

    @staticmethod
    def _dedupe_preserve_order(items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            if not item or item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result

    @staticmethod
    def _localized_section_name(section_name: str) -> str:
        mapping = {
            "abstract": "摘要（Abstract）",
            "introduction": "引言（Introduction）",
            "figures": "图示（Figures）",
            "method": "方法（Method）",
            "experimental_setup": "实验设置（Experimental Setup）",
            "results": "结果（Results）",
            "discussion": "讨论（Discussion）",
            "conclusion": "结论（Conclusion）",
        }
        return mapping.get(section_name, section_name.replace("_", " ").title())
