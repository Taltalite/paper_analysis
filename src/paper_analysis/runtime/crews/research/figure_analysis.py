from __future__ import annotations

import json
import logging
import re
from typing import Protocol

from crewai import Agent, Crew, Process, Task

from paper_analysis.adapters.llm.base import LLMClient
from paper_analysis.domain.models import FigureAnalysis, FigureAnalysisBatch, FigureEvidence, FigureEvidenceBatch
from paper_analysis.domain.schemas import ParsedDocument


class FigureAnalysisRunner(Protocol):
    def run(
        self,
        *,
        document: ParsedDocument,
        figure_evidences: FigureEvidenceBatch,
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
        figure_evidences: FigureEvidenceBatch,
    ) -> FigureAnalysisBatch:
        if not figure_evidences.evidences:
            return FigureAnalysisBatch()
        cleaned_evidence = self._sanitize_batch(figure_evidences)
        if self._llm_client is None:
            return self._fallback_batch(evidences=cleaned_evidence.evidences, reason="未配置 LLM")

        analyst = Agent(
            role=f"论文图表分析助手：{document.title or '未命名文档'}",
            goal=(
                "只基于整理后的图片证据对象，输出实验焦点、主要观察、作者声称结论与图文一致性判断。"
            ),
            backstory=(
                "你是一名严谨的学术图表分析助手。你不会自己重新猜图，"
                "而是严格消费证据对象，区分直接证据与作者进一步解释。"
            ),
            verbose=self._verbose,
            allow_delegation=False,
            llm=self._build_llm(),
        )
        task = Task(
            description=self._build_task_description(document=document, evidence_batch=cleaned_evidence),
            expected_output=(
                "一个严格 JSON 对象，顶层键为 analyses。字段键名保持英文，字段值中的说明性内容使用简体中文。不要输出代码块。"
            ),
            agent=analyst,
            output_pydantic=FigureAnalysisBatch,
        )
        try:
            result = Crew(
                agents=[analyst],
                tasks=[task],
                process=Process.sequential,
                verbose=self._verbose,
            ).kickoff()
            return self._coerce_output(result=result, evidences=cleaned_evidence.evidences)
        except Exception as exc:
            logger.warning("Figure analysis crew 执行失败，回退到保守结果：%s", exc)
            return self._fallback_batch(evidences=cleaned_evidence.evidences, reason=str(exc))

    def _build_llm(self):
        if self._llm_client is None:
            return None
        return self._llm_client.to_crewai_llm()

    @staticmethod
    def _build_task_description(
        *,
        document: ParsedDocument,
        evidence_batch: FigureEvidenceBatch,
    ) -> str:
        evidence_payload = json.dumps(evidence_batch.model_dump(mode="json"), ensure_ascii=False, indent=2)
        return (
            f'请分析题为“{document.title or "未命名文档"}”的论文图表内容。\n\n'
            "你只负责分析 figure / chart / plot / diagram，不承担全文通用总结。\n"
            "你必须严格基于输入的 figure evidence，不能绕过证据对象重新臆测图片。\n"
            "如果 direct_evidence 或 referenced_text_spans 不足，就明确写“不足以判断”，并降低 confidence。\n\n"
            "输入图片证据如下：\n"
            f"{evidence_payload}\n\n"
            "请输出 FigureAnalysisBatch，包含 analyses 列表。每个 figure 对应一项，字段如下：\n"
            "- figure_id\n"
            "- figure_title_or_caption\n"
            "- experiment_focus\n"
            "- compared_items\n"
            "- metrics_or_axes\n"
            "- main_observations\n"
            "- claimed_conclusion\n"
            "- consistency_check\n"
            "- confidence\n\n"
            "规则：\n"
            "- main_observations 只能来自 direct_evidence 与正文引用，不能凭空补图像细节。\n"
            "- claimed_conclusion 需要明确标明是作者声称的结论，而不是图中直接可见事实。\n"
            "- consistency_check 需要指出证据是否足以支撑作者结论。\n"
            "- 说明性内容统一使用简体中文；图号、术语、模型名、数据集名、指标名等可保留原文。\n"
            "- 最终只输出 JSON 对象，不要输出 markdown、解释文字或代码块。\n"
        )

    def _coerce_output(
        self,
        *,
        result: object,
        evidences: list[FigureEvidence],
    ) -> FigureAnalysisBatch:
        structured = getattr(result, "pydantic", None)
        if isinstance(structured, FigureAnalysisBatch):
            return self._sanitize_analysis_batch(structured)
        if isinstance(structured, dict):
            return self._sanitize_batch_payload(structured)

        maybe_dict = getattr(result, "to_dict", None)
        if callable(maybe_dict):
            payload = maybe_dict()
            if isinstance(payload, dict):
                return self._sanitize_batch_payload(payload)

        raw_text = getattr(result, "raw", None)
        if not isinstance(raw_text, str):
            raw_text = str(result)
        return self._parse_batch_text(raw_text=raw_text, evidences=evidences)

    @classmethod
    def _parse_batch_text(
        cls,
        *,
        raw_text: str,
        evidences: list[FigureEvidence],
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
        return cls._fallback_batch(evidences=evidences, reason="；".join(parse_errors))

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
    def _sanitize_batch(cls, evidence_batch: FigureEvidenceBatch) -> FigureEvidenceBatch:
        return FigureEvidenceBatch(
            evidences=[cls._sanitize_evidence(evidence) for evidence in evidence_batch.evidences]
        )

    @classmethod
    def _sanitize_evidence(cls, evidence: FigureEvidence) -> FigureEvidence:
        return FigureEvidence(
            figure_id=cls._sanitize_text(evidence.figure_id, max_length=40),
            figure_title_or_caption=cls._sanitize_text(evidence.figure_title_or_caption, max_length=120),
            page_number=evidence.page_number,
            figure_type=cls._sanitize_text(evidence.figure_type, max_length=60),
            compared_items=cls._sanitize_list(evidence.compared_items, max_items=6, max_length=120),
            metrics_or_axes=cls._sanitize_list(evidence.metrics_or_axes, max_items=6, max_length=80),
            direct_evidence=cls._sanitize_list(evidence.direct_evidence, max_items=6, max_length=200),
            referenced_text_spans=cls._sanitize_list(evidence.referenced_text_spans, max_items=4, max_length=220),
            semantic_source=cls._sanitize_text(evidence.semantic_source, max_length=40),
            evidence_quality=cls._sanitize_text(evidence.evidence_quality, max_length=40) or "不足以判断",
            uncertainties=cls._sanitize_list(evidence.uncertainties, max_items=6, max_length=160),
        )

    @classmethod
    def _sanitize_analysis_batch(cls, batch: FigureAnalysisBatch) -> FigureAnalysisBatch:
        return FigureAnalysisBatch.model_validate(batch.model_dump(mode="json"))

    @classmethod
    def _fallback_batch(
        cls,
        *,
        evidences: list[FigureEvidence],
        reason: str,
    ) -> FigureAnalysisBatch:
        sanitized_reason = cls._sanitize_text(reason, max_length=180) or "模型输出不可解析"
        analyses = [
            FigureAnalysis(
                figure_id=evidence.figure_id,
                figure_title_or_caption=cls._summarize_caption(evidence.figure_title_or_caption),
                experiment_focus=cls._infer_focus(evidence),
                compared_items=evidence.compared_items[:4],
                metrics_or_axes=evidence.metrics_or_axes[:4],
                main_observations=(
                    evidence.direct_evidence[:3]
                    or ["自动回退：当前只保留 caption / 正文引用 / 语义证据中的保守观察。"]
                ),
                claimed_conclusion="不足以判断",
                consistency_check=cls._build_consistency_check(evidence=evidence, reason=sanitized_reason),
                confidence=evidence.evidence_quality or "不足以判断",
            )
            for evidence in evidences
        ]
        return FigureAnalysisBatch(analyses=analyses)

    @classmethod
    def _infer_focus(cls, evidence: FigureEvidence) -> str:
        if evidence.figure_type == "method_diagram":
            return "方法流程与系统组成"
        if evidence.figure_type in {"line_chart", "bar_chart", "result_figure"}:
            return "实验结果比较"
        return "图表语义待进一步确认"

    @classmethod
    def _build_consistency_check(cls, *, evidence: FigureEvidence, reason: str) -> str:
        if evidence.referenced_text_spans and evidence.direct_evidence:
            return f"自动回退：证据对象可用，但未生成更细粒度结论。原因：{reason}"
        return f"自动回退：证据不足，当前无法验证图文一致性。原因：{reason}"

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
