from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from paper_analysis.adapters.llm.base import VisionLLMClient
from paper_analysis.adapters.parser.mcp_figure_semantics import NoopFigureSemanticExtractor
from paper_analysis.domain.models import (
    FigureMetadata,
    FigurePanel,
    FigureSemanticArtifact,
    FigureSemanticArtifactBatch,
)
from paper_analysis.domain.schemas import ParsedDocument

_PROMPT_VERSION = "v1"
_MAX_IMAGES_PER_FIGURE = 4
_CONFIDENCE_VALUES = {"高", "中", "低", "不足以判断"}

_PROMPT_TEMPLATE = """你是一名研究论文图表分析助手。请仔细观察给定论文图表的图片，提取其视觉语义信息。

图表编号：{figure_id}
图注（caption）：{caption}
正文引用片段：{references}

请仅输出一个 JSON 对象（不要输出 Markdown 代码围栏，不要输出其他文字），字段如下：
- "figure_type": 字符串，图表类型（如 method_diagram / line_chart / bar_chart / table_like_figure / result_figure / unknown）
- "visible_text": 字符串数组，图片中实际可见的文字（OCR），每条不超过 160 字
- "axes": 字符串数组，坐标轴含义（无坐标轴则为空数组）
- "legend_items": 字符串数组，图例项（无图例则为空数组）
- "panels": 数组，每个元素为 {{"panel_label": "a", "panel_type": "...", "summary": "...", "confidence": "高|中|低"}}；单面板图表返回空数组
- "direct_evidence": 字符串数组，从图片直接观察到的事实证据（不要复述 caption）
- "uncertainties": 字符串数组，无法确定或图片不清晰之处
- "confidence": 字符串，整体置信度，取 "高"、"中"、"低" 之一

要求：所有说明性文字使用简体中文；模型名、指标名、数据集名等专业术语保留原文；不确定的内容写入 uncertainties，不要编造。"""


class MultimodalFigureSemanticExtractor:
    """通过多模态 LLM（OpenAI 兼容 image_url 协议）抽取图表真实视觉语义。

    任意环节失败（无图片、无视觉配置、HTTP/JSON 异常）都会回退到
    NoopFigureSemanticExtractor 的保守行为，保证 pipeline 不中断。
    """

    def __init__(self, *, vision_client: VisionLLMClient) -> None:
        self._vision_client = vision_client
        self._fallback = NoopFigureSemanticExtractor()

    def extract(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
    ) -> FigureSemanticArtifactBatch:
        artifacts = [self._extract_one(document=document, figure=figure) for figure in figures]
        return FigureSemanticArtifactBatch(artifacts=artifacts)

    def _extract_one(
        self,
        *,
        document: ParsedDocument,
        figure: FigureMetadata,
    ) -> FigureSemanticArtifact:
        try:
            image_paths = self._resolve_image_paths(figure)
            if not image_paths or not self._vision_client.vision_model:
                return self._fallback_one(document=document, figure=figure)

            cache_key = self._cache_key(figure=figure, image_paths=image_paths)
            cache_path = self._cache_path(image_paths[0], cache_key)
            payload = self._read_cache(cache_path)
            if payload is None:
                raw = self._vision_client.complete_with_images(
                    prompt=self._build_prompt(figure),
                    image_paths=image_paths,
                )
                payload = self._parse_payload(raw)
                self._write_cache(cache_path, payload)
            return self._to_artifact(figure=figure, image_paths=image_paths, payload=payload)
        except Exception:
            return self._fallback_one(document=document, figure=figure)

    def _fallback_one(
        self,
        *,
        document: ParsedDocument,
        figure: FigureMetadata,
    ) -> FigureSemanticArtifact:
        return self._fallback.extract(document=document, figures=[figure]).artifacts[0]

    @staticmethod
    def _resolve_image_paths(figure: FigureMetadata) -> list[Path]:
        candidates = [Path(p) for p in figure.image_block_paths[:_MAX_IMAGES_PER_FIGURE]]
        if not candidates and figure.page_snapshot_path:
            candidates = [Path(figure.page_snapshot_path)]
        return [path for path in candidates if path.is_file()]

    def _build_prompt(self, figure: FigureMetadata) -> str:
        references = "；".join(span.strip()[:160] for span in figure.referenced_text_spans[:3]) or "（无）"
        return _PROMPT_TEMPLATE.format(
            figure_id=figure.figure_id or "未知",
            caption=figure.caption.strip()[:400] or "（无）",
            references=references,
        )

    def _cache_key(self, *, figure: FigureMetadata, image_paths: list[Path]) -> str:
        digest = hashlib.sha256()
        digest.update(_PROMPT_VERSION.encode("utf-8"))
        digest.update((self._vision_client.vision_model or "").encode("utf-8"))
        digest.update(figure.figure_id.encode("utf-8"))
        digest.update(figure.caption.encode("utf-8"))
        for path in image_paths:
            digest.update(path.name.encode("utf-8"))
            digest.update(path.read_bytes())
        return digest.hexdigest()

    @staticmethod
    def _cache_path(first_image_path: Path, cache_key: str) -> Path:
        # 图片位于 <assets>/<stem>/images|pages/xxx.png，缓存放到同级 semantic_cache/
        asset_root = first_image_path.parent.parent
        return asset_root / "semantic_cache" / f"{cache_key}.json"

    @staticmethod
    def _read_cache(cache_path: Path) -> dict[str, Any] | None:
        try:
            if cache_path.is_file():
                payload = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
        except (OSError, json.JSONDecodeError):
            return None
        return None

    @staticmethod
    def _write_cache(cache_path: Path, payload: dict[str, Any]) -> None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    @staticmethod
    def _parse_payload(raw: str) -> dict[str, Any]:
        text = raw.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("视觉模型输出中未找到 JSON 对象。")
        payload = json.loads(match.group(0))
        if not isinstance(payload, dict):
            raise ValueError("视觉模型输出不是 JSON 对象。")
        return payload

    @staticmethod
    def _to_artifact(
        *,
        figure: FigureMetadata,
        image_paths: list[Path],
        payload: dict[str, Any],
    ) -> FigureSemanticArtifact:
        confidence = str(payload.get("confidence") or "中")
        if confidence not in _CONFIDENCE_VALUES:
            confidence = "中"
        return FigureSemanticArtifact(
            figure_id=figure.figure_id,
            page_number=figure.page_number,
            figure_type=str(payload.get("figure_type") or "unknown"),
            extraction_source="multimodal_llm",
            page_snapshot_path=figure.page_snapshot_path,
            image_block_paths=[str(path) for path in image_paths],
            crop_path=str(image_paths[0]),
            visible_text=_string_list(payload.get("visible_text")),
            axes=_string_list(payload.get("axes")),
            legend_items=_string_list(payload.get("legend_items")),
            panels=_panels(payload.get("panels"), figure_id=figure.figure_id),
            direct_evidence=_string_list(payload.get("direct_evidence")),
            uncertainties=_string_list(payload.get("uncertainties")),
            confidence=confidence,
        )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _panels(value: Any, *, figure_id: str) -> list[FigurePanel]:
    if not isinstance(value, list):
        return []
    panels: list[FigurePanel] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = str(item.get("panel_label") or "").strip()
        confidence = str(item.get("confidence") or "低")
        if confidence not in _CONFIDENCE_VALUES:
            confidence = "低"
        panels.append(
            FigurePanel(
                panel_id=f"{figure_id}_{label}" if label else figure_id,
                panel_label=label,
                panel_type=str(item.get("panel_type") or "unknown"),
                summary=str(item.get("summary") or ""),
                confidence=confidence,
            )
        )
    return panels
