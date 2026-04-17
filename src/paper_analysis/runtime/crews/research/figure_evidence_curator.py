from __future__ import annotations

import json
import logging
import re
from typing import Protocol

from crewai import Agent, Crew, Process, Task

from paper_analysis.adapters.llm.base import LLMClient
from paper_analysis.domain.models import (
    FigureEvidence,
    FigureEvidenceBatch,
    FigureMetadata,
    FigureSemanticArtifact,
    FigureSemanticArtifactBatch,
)
from paper_analysis.domain.schemas import ParsedDocument


logger = logging.getLogger(__name__)


class FigureEvidenceCuratorRunner(Protocol):
    def run(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
        semantic_artifacts: FigureSemanticArtifactBatch,
    ) -> FigureEvidenceBatch:
        ...


class CrewAIFigureEvidenceCuratorRunner:
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
        semantic_artifacts: FigureSemanticArtifactBatch,
    ) -> FigureEvidenceBatch:
        fallback = self._fallback_batch(figures=figures, semantic_artifacts=semantic_artifacts)
        if not fallback.evidences or self._llm_client is None:
            return fallback

        agent = Agent(
            role=f"论文图片证据整理助手：{document.title or '未命名文档'}",
            goal="把 caption、正文引用和视觉 grounding 结果整理成可供后续图表分析消费的统一证据对象。",
            backstory="你负责证据整合，不负责最终实验结论判断。你必须区分直接证据和不确定项。",
            verbose=self._verbose,
            allow_delegation=False,
            llm=self._llm_client.to_crewai_llm(),
        )
        task = Task(
            description=self._build_task_description(
                document=document,
                figures=figures,
                semantic_artifacts=semantic_artifacts,
            ),
            expected_output="一个严格 JSON 对象，顶层键为 evidences，字段符合 FigureEvidenceBatch。",
            agent=agent,
            output_pydantic=FigureEvidenceBatch,
        )
        try:
            result = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=self._verbose,
            ).kickoff()
            return self._coerce_output(result=result, fallback=fallback)
        except Exception as exc:
            logger.warning("Figure evidence curator crew 执行失败，回退到规则结果：%s", exc)
            return fallback

    @staticmethod
    def _build_task_description(
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
        semantic_artifacts: FigureSemanticArtifactBatch,
    ) -> str:
        figure_payload = json.dumps(
            [figure.model_dump(mode="json") for figure in figures],
            ensure_ascii=False,
            indent=2,
        )
        semantic_payload = json.dumps(semantic_artifacts.model_dump(mode="json"), ensure_ascii=False, indent=2)
        return (
            f'请整理题为“{document.title or "未命名文档"}”的图片证据。\n\n'
            "输入包含 figure metadata 与 grounding 结果。你的职责是：\n"
            "- 给出 figure_type\n"
            "- 整理 metrics_or_axes\n"
            "- 提炼 direct_evidence\n"
            "- 保留 referenced_text_spans\n"
            "- 标注 evidence_quality 与 uncertainties\n"
            "- 不生成作者结论\n\n"
            f"Figure metadata:\n{figure_payload}\n\n"
            f"Grounding artifacts:\n{semantic_payload}\n\n"
            "输出严格 JSON 对象，顶层键为 evidences。"
        )

    @classmethod
    def _coerce_output(
        cls,
        *,
        result: object,
        fallback: FigureEvidenceBatch,
    ) -> FigureEvidenceBatch:
        structured = getattr(result, "pydantic", None)
        if isinstance(structured, FigureEvidenceBatch):
            return cls._sanitize_batch(structured)
        if isinstance(structured, dict):
            return cls._sanitize_payload(structured, fallback=fallback)

        maybe_dict = getattr(result, "to_dict", None)
        if callable(maybe_dict):
            payload = maybe_dict()
            if isinstance(payload, dict):
                return cls._sanitize_payload(payload, fallback=fallback)
        return fallback

    @classmethod
    def _sanitize_payload(
        cls,
        payload: dict[str, object],
        *,
        fallback: FigureEvidenceBatch,
    ) -> FigureEvidenceBatch:
        evidences = payload.get("evidences")
        if not isinstance(evidences, list):
            return fallback
        sanitized = [
            cls._sanitize_evidence(FigureEvidence.model_validate(item))
            for item in evidences
            if isinstance(item, dict)
        ]
        return FigureEvidenceBatch(evidences=sanitized or fallback.evidences)

    @classmethod
    def _sanitize_batch(cls, batch: FigureEvidenceBatch) -> FigureEvidenceBatch:
        return FigureEvidenceBatch(
            evidences=[cls._sanitize_evidence(evidence) for evidence in batch.evidences]
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
    def _fallback_batch(
        cls,
        *,
        figures: list[FigureMetadata],
        semantic_artifacts: FigureSemanticArtifactBatch,
    ) -> FigureEvidenceBatch:
        artifact_map = {artifact.figure_id: artifact for artifact in semantic_artifacts.artifacts}
        evidences = [
            cls._fallback_evidence(figure=figure, artifact=artifact_map.get(figure.figure_id))
            for figure in figures
        ]
        return FigureEvidenceBatch(evidences=evidences)

    @classmethod
    def _fallback_evidence(
        cls,
        *,
        figure: FigureMetadata,
        artifact: FigureSemanticArtifact | None,
    ) -> FigureEvidence:
        figure_type = artifact.figure_type if artifact and artifact.figure_type else "unknown"
        metrics = artifact.axes if artifact else []
        direct_evidence = list(artifact.direct_evidence if artifact else [])
        if figure.caption:
            direct_evidence.insert(0, f"caption 摘要：{cls._sanitize_text(figure.caption, max_length=120)}")
        return FigureEvidence(
            figure_id=cls._sanitize_text(figure.figure_id, max_length=40),
            figure_title_or_caption=cls._sanitize_text(figure.caption, max_length=120),
            page_number=figure.page_number,
            figure_type=figure_type,
            compared_items=cls._infer_compared_items(figure),
            metrics_or_axes=cls._sanitize_list(metrics, max_items=6, max_length=80),
            direct_evidence=cls._sanitize_list(direct_evidence, max_items=6, max_length=200),
            referenced_text_spans=cls._sanitize_list(figure.referenced_text_spans, max_items=4, max_length=220),
            semantic_source=artifact.extraction_source if artifact else "unknown",
            evidence_quality=(artifact.confidence if artifact else "低") or "不足以判断",
            uncertainties=cls._sanitize_list(artifact.uncertainties if artifact else [], max_items=6, max_length=160),
        )

    @classmethod
    def _infer_compared_items(cls, figure: FigureMetadata) -> list[str]:
        text = " ".join([figure.caption, *figure.referenced_text_spans])
        parts = re.split(r"\b(vs\.?|versus|compared with|against)\b", text, flags=re.IGNORECASE)
        if len(parts) >= 3:
            return [cls._sanitize_text(parts[0], max_length=60), cls._sanitize_text(parts[-1], max_length=60)]
        return []

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
