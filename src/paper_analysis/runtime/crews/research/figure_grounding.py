from __future__ import annotations

import json
import logging
import re
from typing import Protocol

from crewai import Agent, Crew, Process, Task

from paper_analysis.adapters.llm.base import LLMClient
from paper_analysis.adapters.parser.figure_semantics_base import FigureSemanticExtractor
from paper_analysis.domain.models import FigureMetadata, FigureSemanticArtifact, FigureSemanticArtifactBatch
from paper_analysis.domain.schemas import ParsedDocument


logger = logging.getLogger(__name__)


class FigureGroundingRunner(Protocol):
    def run(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
    ) -> FigureSemanticArtifactBatch:
        ...


class CrewAIFigureGroundingRunner:
    def __init__(
        self,
        *,
        extractor: FigureSemanticExtractor,
        llm_client: LLMClient | None = None,
        verbose: bool = True,
    ) -> None:
        self._extractor = extractor
        self._llm_client = llm_client
        self._verbose = verbose

    def run(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
    ) -> FigureSemanticArtifactBatch:
        coarse_batch = self._extractor.extract(document=document, figures=figures)
        if not coarse_batch.artifacts or self._llm_client is None:
            return self._sanitize_batch(coarse_batch)

        agent = Agent(
            role=f"论文图片 grounding 助手：{document.title or '未命名文档'}",
            goal="基于图片语义提取结果，归一化每个 figure 的视觉证据、图类型、panel 信息与不确定性。",
            backstory="你只负责视觉 grounding，不做论文结论推断，不把作者主张误写成图像直接证据。",
            verbose=self._verbose,
            allow_delegation=False,
            llm=self._llm_client.to_crewai_llm(),
        )
        task = Task(
            description=self._build_task_description(document=document, batch=coarse_batch),
            expected_output="一个严格 JSON 对象，顶层键为 artifacts，字段符合 FigureSemanticArtifactBatch。",
            agent=agent,
            output_pydantic=FigureSemanticArtifactBatch,
        )
        try:
            result = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=self._verbose,
            ).kickoff()
            return self._coerce_output(result=result, coarse_batch=coarse_batch)
        except Exception as exc:
            logger.warning("Figure grounding crew 执行失败，回退到 extractor 输出：%s", exc)
            return self._sanitize_batch(coarse_batch)

    @staticmethod
    def _build_task_description(
        *,
        document: ParsedDocument,
        batch: FigureSemanticArtifactBatch,
    ) -> str:
        payload = json.dumps(batch.model_dump(mode="json"), ensure_ascii=False, indent=2)
        return (
            f'请对题为“{document.title or "未命名文档"}”的 figure grounding 结果做归一化。\n\n'
            "输入来自 parser / MCP adapter 的初步视觉语义证据。你的职责是：\n"
            "- 统一 figure_type 命名\n"
            "- 清洗 visible_text / axes / legend_items\n"
            "- 保留 direct_evidence\n"
            "- 明确 uncertainties\n"
            "- 不做实验结论推断\n\n"
            "输入 JSON：\n"
            f"{payload}\n\n"
            "请输出严格 JSON 对象，顶层键为 artifacts。\n"
            "字段说明内容统一使用简体中文；术语、指标名、模型名可保留原文。"
        )

    @classmethod
    def _coerce_output(
        cls,
        *,
        result: object,
        coarse_batch: FigureSemanticArtifactBatch,
    ) -> FigureSemanticArtifactBatch:
        structured = getattr(result, "pydantic", None)
        if isinstance(structured, FigureSemanticArtifactBatch):
            return cls._sanitize_batch(structured)
        if isinstance(structured, dict):
            return cls._sanitize_payload(structured, coarse_batch=coarse_batch)

        maybe_dict = getattr(result, "to_dict", None)
        if callable(maybe_dict):
            payload = maybe_dict()
            if isinstance(payload, dict):
                return cls._sanitize_payload(payload, coarse_batch=coarse_batch)
        return cls._sanitize_batch(coarse_batch)

    @classmethod
    def _sanitize_payload(
        cls,
        payload: dict[str, object],
        *,
        coarse_batch: FigureSemanticArtifactBatch,
    ) -> FigureSemanticArtifactBatch:
        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, list):
            return cls._sanitize_batch(coarse_batch)
        sanitized = [
            cls._sanitize_artifact(FigureSemanticArtifact.model_validate(item))
            for item in artifacts
            if isinstance(item, dict)
        ]
        return FigureSemanticArtifactBatch(artifacts=sanitized or coarse_batch.artifacts)

    @classmethod
    def _sanitize_batch(cls, batch: FigureSemanticArtifactBatch) -> FigureSemanticArtifactBatch:
        return FigureSemanticArtifactBatch(
            artifacts=[cls._sanitize_artifact(artifact) for artifact in batch.artifacts]
        )

    @classmethod
    def _sanitize_artifact(cls, artifact: FigureSemanticArtifact) -> FigureSemanticArtifact:
        return FigureSemanticArtifact(
            figure_id=cls._sanitize_text(artifact.figure_id, max_length=40),
            page_number=artifact.page_number,
            figure_type=cls._sanitize_text(artifact.figure_type, max_length=60),
            extraction_source=cls._sanitize_text(artifact.extraction_source, max_length=40),
            page_snapshot_path=cls._sanitize_text(artifact.page_snapshot_path or "", max_length=240) or None,
            image_block_paths=cls._sanitize_list(artifact.image_block_paths, max_items=6, max_length=240),
            crop_path=cls._sanitize_text(artifact.crop_path or "", max_length=240) or None,
            visible_text=cls._sanitize_list(artifact.visible_text, max_items=6, max_length=160),
            axes=cls._sanitize_list(artifact.axes, max_items=6, max_length=80),
            legend_items=cls._sanitize_list(artifact.legend_items, max_items=8, max_length=80),
            panels=artifact.panels[:8],
            direct_evidence=cls._sanitize_list(artifact.direct_evidence, max_items=6, max_length=200),
            uncertainties=cls._sanitize_list(artifact.uncertainties, max_items=6, max_length=160),
            confidence=cls._sanitize_text(artifact.confidence, max_length=40) or "不足以判断",
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
