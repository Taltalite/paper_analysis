from __future__ import annotations

import json
import logging
import re
from typing import Protocol

from crewai import Agent, Crew, Process, Task

from paper_analysis.adapters.llm.base import LLMClient
from paper_analysis.domain.models import DocumentBlock, DocumentStructureDraft, FigureMetadata
from paper_analysis.domain.schemas import ParsedDocument


logger = logging.getLogger(__name__)


class DocumentStructuringRunner(Protocol):
    def run(self, *, document: ParsedDocument) -> DocumentStructureDraft:
        ...


class CrewAIDocumentStructuringRunner:
    _SECTION_ALIASES = {
        "abstract": "abstract",
        "introduction": "introduction",
        "background": "introduction",
        "method": "method",
        "methods": "method",
        "materials and methods": "method",
        "experimental setup": "experimental_setup",
        "experimental section": "experimental_setup",
        "experimental procedures": "experimental_setup",
        "results": "results",
        "discussion": "discussion",
        "results and discussion": "results",
        "conclusion": "conclusion",
        "conclusions": "conclusion",
    }

    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        verbose: bool = True,
    ) -> None:
        self._llm_client = llm_client
        self._verbose = verbose

    def run(self, *, document: ParsedDocument) -> DocumentStructureDraft:
        coarse_draft = self._coarse_draft(document)
        ordered_blocks = self._ordered_blocks(document)
        if not ordered_blocks:
            return coarse_draft

        agent = Agent(
            role=f"论文结构校正助手：{document.title or '未命名文档'}",
            goal=(
                "基于按顺序提取的 PDF block、粗规则切分结果和 figure metadata，"
                "校正论文元数据、章节归属、图注与正文引用映射。"
            ),
            backstory=(
                "你是一名严谨的文档结构分析助手。你不会直接做论文结论分析，"
                "只负责把顺序化内容整理成可靠的结构化文档草稿。"
            ),
            verbose=self._verbose,
            allow_delegation=False,
            llm=self._build_llm(),
        )
        task = Task(
            description=self._build_task_description(
                document=document,
                ordered_blocks=ordered_blocks,
                coarse_draft=coarse_draft,
            ),
            expected_output="一个严格 JSON 对象，字段符合 DocumentStructureDraft。",
            agent=agent,
        )
        try:
            result = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=self._verbose,
            ).kickoff()
            return self._coerce_output(result=result, coarse_draft=coarse_draft)
        except Exception as exc:
            logger.warning("Document structuring crew 执行失败，回退到粗结构：%s", exc)
            return coarse_draft

    def _build_llm(self):
        if self._llm_client is None:
            return None
        return self._llm_client.to_crewai_llm()

    @classmethod
    def _coerce_output(
        cls,
        *,
        result: object,
        coarse_draft: DocumentStructureDraft,
    ) -> DocumentStructureDraft:
        structured = getattr(result, "pydantic", None)
        if isinstance(structured, dict):
            return cls._sanitize_draft_payload(structured, coarse_draft=coarse_draft)
        if isinstance(structured, DocumentStructureDraft):
            return structured

        maybe_dict = getattr(result, "to_dict", None)
        if callable(maybe_dict):
            payload = maybe_dict()
            if isinstance(payload, dict):
                return cls._sanitize_draft_payload(payload, coarse_draft=coarse_draft)

        raw_text = getattr(result, "raw", None)
        if not isinstance(raw_text, str):
            raw_text = str(result)
        return cls._parse_draft_text(raw_text=raw_text, coarse_draft=coarse_draft)

    @classmethod
    def _parse_draft_text(
        cls,
        *,
        raw_text: str,
        coarse_draft: DocumentStructureDraft,
    ) -> DocumentStructureDraft:
        cleaned = cls._sanitize_text(raw_text, max_length=120000)
        json_block = cls._extract_json_block(cleaned)
        if json_block is None:
            return coarse_draft

        for candidate in (json_block, cls._escape_control_chars_in_json_strings(json_block)):
            try:
                payload = json.loads(candidate)
                if isinstance(payload, dict):
                    return cls._sanitize_draft_payload(payload, coarse_draft=coarse_draft)
            except json.JSONDecodeError:
                continue
        return coarse_draft

    @classmethod
    def _sanitize_draft_payload(
        cls,
        payload: dict[str, object],
        *,
        coarse_draft: DocumentStructureDraft,
    ) -> DocumentStructureDraft:
        sections_payload = payload.get("sections")
        sections = sections_payload if isinstance(sections_payload, dict) else {}
        figures_payload = payload.get("figures")
        figures = figures_payload if isinstance(figures_payload, list) else []

        sanitized_sections: dict[str, str] = {}
        for key, value in sections.items():
            key_text = cls._canonical_section_key(cls._sanitize_text(key, max_length=40).lower())
            value_text = cls._sanitize_text(value, max_length=6000)
            if key_text and value_text:
                sanitized_sections[key_text] = value_text

        sanitized_figures: list[FigureMetadata] = []
        for item in figures:
            if not isinstance(item, dict):
                continue
            sanitized_figures.append(
                FigureMetadata(
                    figure_id=cls._sanitize_text(item.get("figure_id", ""), max_length=40),
                    caption=cls._sanitize_text(item.get("caption", ""), max_length=800),
                    page_number=cls._coerce_int(item.get("page_number")),
                    page_snapshot_path=cls._sanitize_text(item.get("page_snapshot_path", ""), max_length=240) or None,
                    referenced_text_spans=cls._sanitize_list(item.get("referenced_text_spans"), max_items=6, max_length=260),
                    caption_block_ids=cls._sanitize_list(item.get("caption_block_ids"), max_items=8, max_length=40),
                    reference_block_ids=cls._sanitize_list(item.get("reference_block_ids"), max_items=12, max_length=40),
                )
            )

        merged_sections = dict(coarse_draft.sections)
        merged_sections.update(sanitized_sections)
        section_order = [
            cls._canonical_section_key(item)
            for item in cls._sanitize_list(payload.get("section_order"), max_items=20, max_length=40)
        ]
        if not section_order:
            section_order = list(merged_sections.keys())

        return DocumentStructureDraft(
            title=cls._sanitize_text(payload.get("title", ""), max_length=300) or coarse_draft.title,
            authors=cls._sanitize_list(payload.get("authors"), max_items=30, max_length=80) or coarse_draft.authors,
            doi=cls._sanitize_text(payload.get("doi", ""), max_length=120) or coarse_draft.doi,
            venue=cls._sanitize_text(payload.get("venue", ""), max_length=200) or coarse_draft.venue,
            year=cls._sanitize_text(payload.get("year", ""), max_length=20) or coarse_draft.year,
            abstract=cls._sanitize_text(payload.get("abstract", ""), max_length=5000) or coarse_draft.abstract,
            sections=merged_sections,
            section_order=section_order,
            figures=sanitized_figures or coarse_draft.figures,
            discarded_noise=cls._sanitize_list(payload.get("discarded_noise"), max_items=30, max_length=160) or coarse_draft.discarded_noise,
            uncertainties=cls._sanitize_list(payload.get("uncertainties"), max_items=20, max_length=160) or coarse_draft.uncertainties,
        )

    @classmethod
    def _build_task_description(
        cls,
        *,
        document: ParsedDocument,
        ordered_blocks: list[DocumentBlock],
        coarse_draft: DocumentStructureDraft,
    ) -> str:
        block_lines: list[str] = []
        for block in ordered_blocks:
            if block.block_type == "image":
                block_lines.append(
                    f"- {block.block_id} | page={block.page_number} | type=image | image_path={block.image_path or '未提供'}"
                )
            else:
                block_lines.append(
                    f"- {block.block_id} | page={block.page_number} | type=text | text={cls._sanitize_text(block.text, max_length=240)}"
                )

        coarse_json = json.dumps(coarse_draft.model_dump(mode="json"), ensure_ascii=False, indent=2)
        return (
            f'请对题为“{document.title or "未命名文档"}”的 PDF 顺序化提取结果做结构校正。\n\n'
            "输入包含按阅读顺序提取的 text/image block，以及规则层生成的粗结构草稿。\n"
            "你的职责不是做论文结论分析，而是校正元数据、章节边界、figure-caption-reference 关系，并剔除噪声。\n\n"
            "按顺序提取的 blocks：\n"
            + "\n".join(block_lines)
            + "\n\n粗结构草稿：\n"
            + coarse_json
            + "\n\n"
            "请输出严格 JSON 对象，字段如下：\n"
            "- title\n"
            "- authors\n"
            "- doi\n"
            "- venue\n"
            "- year\n"
            "- abstract\n"
            "- sections\n"
            "- section_order\n"
            "- figures\n"
            "- discarded_noise\n"
            "- uncertainties\n\n"
            "规则：\n"
            "- 优先依据 block 顺序和明确章节标题进行判断。\n"
            "- 标题不能误用期刊页眉、引用行或下载页眉。\n"
            "- 作者不能混入摘要正文或机构脚注。\n"
            "- DOI 必须是完整、可信的论文 DOI；不确定时返回空字符串。\n"
            "- figures 中每项至少包含 figure_id、caption、page_number、referenced_text_spans。\n"
            "- 如果某个图主要是方法示意图而非结果图，只需保留可靠 caption 和引用，不要臆造实验结论。\n"
            "- 说明性内容使用简体中文；论文标题、作者名、期刊名、图号、术语可保留原文。\n"
            "- 只输出 JSON 对象，不要输出解释文字、markdown 或代码块。\n"
        )

    @staticmethod
    def _coarse_draft(document: ParsedDocument) -> DocumentStructureDraft:
        payload = document.metadata.get("coarse_structure")
        if isinstance(payload, dict):
            try:
                return DocumentStructureDraft.model_validate(payload)
            except Exception:
                pass
        return DocumentStructureDraft(
            title=document.title,
            sections=document.sections,
            section_order=document.section_order,
            figures=document.figures,
            authors=[],
        )

    @staticmethod
    def _ordered_blocks(document: ParsedDocument) -> list[DocumentBlock]:
        payload = document.metadata.get("ordered_blocks")
        if not isinstance(payload, list):
            return []
        blocks: list[DocumentBlock] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                blocks.append(DocumentBlock.model_validate(item))
            except Exception:
                continue
        return blocks

    @staticmethod
    def _sanitize_text(value: object, *, max_length: int = 500) -> str:
        text = "" if value is None else str(value)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_length].strip()

    @classmethod
    def _sanitize_list(
        cls,
        value: object,
        *,
        max_items: int = 8,
        max_length: int = 120,
    ) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            value = [value]
        sanitized: list[str] = []
        for item in value:
            text = cls._sanitize_text(item, max_length=max_length)
            if text:
                sanitized.append(text)
            if len(sanitized) >= max_items:
                break
        return sanitized

    @staticmethod
    def _coerce_int(value: object) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _canonical_section_key(cls, value: str) -> str:
        normalized = re.sub(r"[^a-z ]+", " ", value.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return cls._SECTION_ALIASES.get(normalized, normalized)

    @classmethod
    def _extract_json_block(cls, text: str) -> str | None:
        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
        if fenced:
            return fenced.group(1)
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return text[start : end + 1]

    @staticmethod
    def _escape_control_chars_in_json_strings(text: str) -> str:
        result: list[str] = []
        in_string = False
        escaped = False
        for char in text:
            if escaped:
                result.append(char)
                escaped = False
                continue
            if char == "\\":
                result.append(char)
                escaped = True
                continue
            if char == '"':
                result.append(char)
                in_string = not in_string
                continue
            if in_string and char == "\n":
                result.append("\\n")
                continue
            if in_string and char == "\t":
                result.append("\\t")
                continue
            if in_string and ord(char) < 32:
                result.append(" ")
                continue
            result.append(char)
        return "".join(result)
