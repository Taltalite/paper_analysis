from __future__ import annotations

import re

from paper_analysis.adapters.parser.figure_semantics_base import FigureSemanticExtractor
from paper_analysis.domain.models import (
    FigureMetadata,
    FigurePanel,
    FigureSemanticArtifact,
    FigureSemanticArtifactBatch,
)
from paper_analysis.domain.schemas import ParsedDocument


class NoopFigureSemanticExtractor(FigureSemanticExtractor):
    """Fallback extractor that preserves a stable contract before MCP integration is ready."""

    def extract(
        self,
        *,
        document: ParsedDocument,
        figures: list[FigureMetadata],
    ) -> FigureSemanticArtifactBatch:
        artifacts = [
            FigureSemanticArtifact(
                figure_id=figure.figure_id,
                page_number=figure.page_number,
                figure_type=self._infer_figure_type(figure),
                extraction_source="noop",
                page_snapshot_path=figure.page_snapshot_path,
                image_block_paths=figure.image_block_paths[:4],
                crop_path=figure.image_block_paths[0] if figure.image_block_paths else None,
                visible_text=self._visible_text(figure),
                axes=self._infer_axes(figure),
                legend_items=[],
                panels=self._infer_panels(figure),
                direct_evidence=self._direct_evidence(figure),
                uncertainties=self._uncertainties(figure),
                confidence="低" if not figure.image_block_paths else "中",
            )
            for figure in figures
        ]
        return FigureSemanticArtifactBatch(artifacts=artifacts)

    @staticmethod
    def _infer_figure_type(figure: FigureMetadata) -> str:
        text = " ".join([figure.caption, *figure.referenced_text_spans]).lower()
        if any(token in text for token in ("workflow", "pipeline", "framework", "overview", "architecture")):
            return "method_diagram"
        if any(token in text for token in ("plot", "curve", "trend", "line chart")):
            return "line_chart"
        if any(token in text for token in ("bar", "histogram")):
            return "bar_chart"
        if any(token in text for token in ("table",)):
            return "table_like_figure"
        if any(token in text for token in ("compare", "performance", "accuracy", "results", "ablation")):
            return "result_figure"
        return "unknown"

    @staticmethod
    def _visible_text(figure: FigureMetadata) -> list[str]:
        snippets = [figure.caption, *figure.referenced_text_spans[:2]]
        return [snippet.strip()[:160] for snippet in snippets if snippet.strip()][:4]

    @staticmethod
    def _infer_axes(figure: FigureMetadata) -> list[str]:
        text = " ".join([figure.caption, *figure.referenced_text_spans])
        candidates = []
        for key in ("accuracy", "f1", "precision", "recall", "latency", "speed", "time", "loss"):
            if re.search(rf"\b{re.escape(key)}\b", text, flags=re.IGNORECASE):
                candidates.append(key)
        return candidates[:4]

    @staticmethod
    def _infer_panels(figure: FigureMetadata) -> list[FigurePanel]:
        labels = re.findall(r"\(([a-z])\)", figure.caption, flags=re.IGNORECASE)
        return [
            FigurePanel(
                panel_id=f"{figure.figure_id}_{label.lower()}",
                panel_label=label.lower(),
                panel_type="unknown",
                summary=f"基于 caption 检测到 panel ({label.lower()})。",
                confidence="低",
            )
            for label in labels[:6]
        ]

    @staticmethod
    def _direct_evidence(figure: FigureMetadata) -> list[str]:
        evidence: list[str] = []
        if figure.caption:
            evidence.append(f"caption 提供了图的主要语义线索：{figure.caption[:120]}")
        if figure.referenced_text_spans:
            evidence.extend(
                f"正文引用提到：{span[:120]}" for span in figure.referenced_text_spans[:2] if span.strip()
            )
        if figure.image_block_paths:
            evidence.append("PDF 解析阶段已关联到局部图片块，可作为后续 MCP 视觉切分输入。")
        elif figure.page_snapshot_path:
            evidence.append("当前仅有整页截图，局部图区域仍需后续 MCP grounding。")
        return evidence[:5]

    @staticmethod
    def _uncertainties(figure: FigureMetadata) -> list[str]:
        uncertainties: list[str] = []
        if not figure.image_block_paths:
            uncertainties.append("尚未关联精确 figure crop，当前语义主要来自 caption 和正文引用。")
        if not figure.referenced_text_spans:
            uncertainties.append("正文缺少明确引用段落，图文一致性证据较弱。")
        return uncertainties[:4]


class MCPFigureSemanticExtractor(NoopFigureSemanticExtractor):
    """Placeholder MCP adapter. Falls back to stable noop semantics until a concrete MCP client is wired in."""

    pass
