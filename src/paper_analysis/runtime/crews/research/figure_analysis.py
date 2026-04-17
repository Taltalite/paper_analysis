from __future__ import annotations

import json
import logging
import re
from typing import Protocol

from crewai import Agent, Crew, Process, Task

from paper_analysis.adapters.llm.base import LLMClient
from paper_analysis.domain.models import FigureAnalysis, FigureAnalysisBatch, FigureMetadata
from paper_analysis.domain.schemas import ParsedDocument


class FigureAnalysisRunner(Protocol):
    def run(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
    ) -> FigureAnalysisBatch:
        ...


logger = logging.getLogger(__name__)


class CrewAIFigureAnalysisRunner:
    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        verbose: bool = True,
    ) -> None:
        self._llm_client = llm_client
        self._verbose = verbose

    def run(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
    ) -> FigureAnalysisBatch:
        if not figures:
            return FigureAnalysisBatch()
        cleaned_figures = [self._sanitize_figure_metadata(figure) for figure in figures]

        analyst = Agent(
            role=f"论文图表分析助手：{document.title or '未命名文档'}",
            goal=(
                "只分析论文中的 figure、chart、plot、diagram 相关内容，"
                "基于 caption、正文引用与图像页上下文提取客观观察、作者声称结论和图文一致性判断。"
            ),
            backstory=(
                "你是一名严谨的学术图表分析助手。你先看图注（caption），再看正文中引用该图的段落，"
                "最后结合图页上下文进行辅助判断。你会明确区分图中直接显示的现象与作者进一步解释的结论。"
            ),
            verbose=self._verbose,
            allow_delegation=False,
            llm=self._build_llm(),
        )
        task = Task(
            description=self._build_task_description(document=document, figures=cleaned_figures),
            expected_output=(
                "一个严格 JSON 对象，顶层键为 analyses。字段键名保持英文，字段值中的说明性内容使用简体中文。不要输出代码块。"
            ),
            agent=analyst,
        )
        try:
            result = Crew(
                agents=[analyst],
                tasks=[task],
                process=Process.sequential,
                verbose=self._verbose,
            ).kickoff()
            return self._coerce_output(result=result, figures=cleaned_figures)
        except Exception as exc:
            logger.warning("Figure analysis crew 执行失败，回退到保守结果：%s", exc)
            return self._fallback_batch(figures=cleaned_figures, reason=str(exc))

    def _build_llm(self):
        if self._llm_client is None:
            return None
        return self._llm_client.to_crewai_llm()

    @staticmethod
    def _build_task_description(
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
    ) -> str:
        figure_blocks: list[str] = []
        for figure in figures:
            refs = "\n".join(f"- {item}" for item in figure.referenced_text_spans) or "- 未明确说明"
            figure_blocks.append(
                "\n".join(
                    [
                        f"### {figure.figure_id or '未编号图表'}",
                        f"- caption: {figure.caption or '未明确说明'}",
                        f"- page_number: {figure.page_number if figure.page_number is not None else '未明确说明'}",
                        f"- page_snapshot_path: {figure.page_snapshot_path or '未提供'}",
                        "- referenced_text_spans:",
                        refs,
                    ]
                )
            )
        figures_text = "\n\n".join(figure_blocks)
        return (
            f'请分析题为“{document.title or "未命名文档"}”的论文图表内容。\n\n'
            "你只负责分析 figure / chart / plot / diagram，不承担全文通用总结。\n"
            "分析顺序必须遵循：先看 caption，再看正文中引用该 figure 的段落，最后结合图页上下文辅助判断。\n"
            "如果 caption、正文引用或图页上下文不足，就明确写“不足以判断”，并降低 confidence。\n\n"
            "输入图表上下文如下：\n"
            f"{figures_text}\n\n"
            "请输出 FigureAnalysisBatch，包含 analyses 列表。每个 figure 对应一项，字段如下：\n"
            "- figure_id\n"
            "- figure_title_or_caption（用一句中文概括图注，不要原样逐字复制完整 caption，最长 80 字）\n"
            "- experiment_focus\n"
            "- compared_items\n"
            "- metrics_or_axes\n"
            "- main_observations\n"
            "- claimed_conclusion\n"
            "- consistency_check\n"
            "- confidence\n\n"
            "规则：\n"
            "- 不允许脱离 caption 和正文引用孤立臆测图像含义。\n"
            "- 先写图中客观可见的信息，再总结作者声称的结论。\n"
            "- 明确区分“图中直接显示的现象”和“作者进一步解释/推断的结论”。\n"
            "- 除 figure_id 外，不要机械复制原始 caption；优先用简洁中文转述。\n"
            "- 说明性内容统一使用简体中文；图号、术语、模型名、数据集名、指标名等可保留原文。\n"
            "- 若图像质量不足、坐标轴不可读、图例缺失或正文引用不足，必须在 consistency_check 或 confidence 中说明原因。\n"
            "- 最终只输出 JSON 对象，不要输出 markdown、解释文字或代码块。\n"
        )

    def _coerce_output(
        self,
        *,
        result: object,
        figures: list[FigureMetadata],
    ) -> FigureAnalysisBatch:
        structured = getattr(result, "pydantic", None)
        if isinstance(structured, dict):
            return self._sanitize_batch_payload(structured)
        if isinstance(structured, FigureAnalysisBatch):
            return structured

        maybe_dict = getattr(result, "to_dict", None)
        if callable(maybe_dict):
            payload = maybe_dict()
            if isinstance(payload, dict):
                return self._sanitize_batch_payload(payload)

        raw_text = getattr(result, "raw", None)
        if not isinstance(raw_text, str):
            raw_text = str(result)
        return self._parse_batch_text(raw_text=raw_text, figures=figures)

    @classmethod
    def _parse_batch_text(
        cls,
        *,
        raw_text: str,
        figures: list[FigureMetadata],
    ) -> FigureAnalysisBatch:
        cleaned = cls._sanitize_text(raw_text)
        json_block = cls._extract_json_block(cleaned)
        if json_block is None:
            raise ValueError("Figure analysis 未返回可识别的 JSON 对象。")

        parse_errors: list[str] = []
        candidates = [
            json_block,
            cls._escape_control_chars_in_json_strings(json_block),
        ]
        for candidate in candidates:
            try:
                payload = json.loads(candidate)
                if isinstance(payload, dict):
                    return cls._sanitize_batch_payload(payload)
            except json.JSONDecodeError as exc:
                parse_errors.append(str(exc))

        logger.warning("Figure analysis JSON 解析失败，尝试回退。errors=%s", parse_errors)
        return cls._fallback_batch(figures=figures, reason="；".join(parse_errors))

    @classmethod
    def _sanitize_batch_payload(cls, payload: dict[str, object]) -> FigureAnalysisBatch:
        analyses = payload.get("analyses")
        if not isinstance(analyses, list):
            analyses = []
        sanitized_analyses: list[dict[str, object]] = []
        for item in analyses:
            if not isinstance(item, dict):
                continue
            sanitized_analyses.append(
                {
                    "figure_id": cls._sanitize_text(item.get("figure_id", "")),
                    "figure_title_or_caption": cls._sanitize_text(item.get("figure_title_or_caption", ""), max_length=120),
                    "experiment_focus": cls._sanitize_text(item.get("experiment_focus", ""), max_length=240),
                    "compared_items": cls._sanitize_list(item.get("compared_items")),
                    "metrics_or_axes": cls._sanitize_list(item.get("metrics_or_axes")),
                    "main_observations": cls._sanitize_list(item.get("main_observations"), max_items=5),
                    "claimed_conclusion": cls._sanitize_text(item.get("claimed_conclusion", ""), max_length=280),
                    "consistency_check": cls._sanitize_text(item.get("consistency_check", ""), max_length=280),
                    "confidence": cls._sanitize_text(item.get("confidence", "不足以判断"), max_length=40) or "不足以判断",
                }
            )
        return FigureAnalysisBatch.model_validate({"analyses": sanitized_analyses})

    @classmethod
    def _fallback_batch(
        cls,
        *,
        figures: list[FigureMetadata],
        reason: str,
    ) -> FigureAnalysisBatch:
        sanitized_reason = cls._sanitize_text(reason, max_length=180) or "模型输出不可解析"
        analyses = [
            FigureAnalysis(
                figure_id=figure.figure_id,
                figure_title_or_caption=cls._summarize_caption(figure.caption),
                experiment_focus="不足以判断",
                compared_items=[],
                metrics_or_axes=[],
                main_observations=["自动回退：figure 结构化输出失败，未对图像内容做进一步臆测。"],
                claimed_conclusion="不足以判断",
                consistency_check=f"自动回退，原因：{sanitized_reason}",
                confidence="不足以判断",
            )
            for figure in figures
        ]
        return FigureAnalysisBatch(analyses=analyses)

    @classmethod
    def _sanitize_figure_metadata(cls, figure: FigureMetadata) -> FigureMetadata:
        return FigureMetadata(
            figure_id=cls._sanitize_text(figure.figure_id, max_length=40),
            caption=cls._sanitize_text(figure.caption, max_length=500),
            page_number=figure.page_number,
            page_snapshot_path=cls._sanitize_text(figure.page_snapshot_path or "", max_length=240) or None,
            referenced_text_spans=cls._sanitize_list(figure.referenced_text_spans, max_items=3, max_length=260),
        )

    @staticmethod
    def _sanitize_text(value: object, *, max_length: int = 320) -> str:
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
        max_items: int = 4,
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

    @classmethod
    def _summarize_caption(cls, caption: str) -> str:
        sanitized = cls._sanitize_text(caption, max_length=80)
        if not sanitized:
            return "未明确说明"
        return sanitized
