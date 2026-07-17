import json
import tempfile
import unittest
from pathlib import Path

from paper_analysis.adapters.parser.mcp_figure_semantics import NoopFigureSemanticExtractor
from paper_analysis.adapters.parser.multimodal_figure_semantics import (
    MultimodalFigureSemanticExtractor,
)
from paper_analysis.domain.models import FigureMetadata
from paper_analysis.domain.schemas import ParsedDocument


class _FakeVisionClient:
    def __init__(self, response: str, *, vision_model: str | None = "fake-vision") -> None:
        self._response = response
        self._vision_model = vision_model
        self.calls: list[dict] = []

    @property
    def vision_model(self) -> str | None:
        return self._vision_model

    def complete_with_images(self, *, prompt: str, image_paths: list[Path]) -> str:
        self.calls.append({"prompt": prompt, "image_paths": image_paths})
        return self._response


def _make_figure(asset_root: Path, *, image_count: int = 1) -> FigureMetadata:
    image_dir = asset_root / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_paths = []
    for index in range(image_count):
        image_path = image_dir / f"p1_b{index}.png"
        image_path.write_bytes(b"\x89PNG-fake-%d" % index)
        image_paths.append(str(image_path))
    return FigureMetadata(
        figure_id="Figure 1",
        caption="Figure 1 compares accuracy and latency of different methods.",
        page_number=1,
        image_block_paths=image_paths,
        referenced_text_spans=["As shown in Figure 1, our method improves accuracy."],
    )


class FigureSemanticExtractorTest(unittest.TestCase):
    def test_noop_extractor_builds_stable_semantic_artifact(self) -> None:
        extractor = NoopFigureSemanticExtractor()
        batch = extractor.extract(
            document=ParsedDocument(title="Test Paper"),
            figures=[
                FigureMetadata(
                    figure_id="Figure 1",
                    caption="Figure 1 compares accuracy and latency of different methods.",
                    page_number=2,
                    page_snapshot_path="output/page-2.png",
                    image_block_paths=["output/figure-1.png"],
                    referenced_text_spans=["As shown in Figure 1, our method improves accuracy."],
                )
            ],
        )

        self.assertEqual(len(batch.artifacts), 1)
        artifact = batch.artifacts[0]
        self.assertEqual(artifact.figure_id, "Figure 1")
        self.assertEqual(artifact.extraction_source, "noop")
        self.assertIn("accuracy", artifact.axes)
        self.assertEqual(artifact.crop_path, "output/figure-1.png")
        self.assertTrue(artifact.direct_evidence)


class MultimodalFigureSemanticExtractorTest(unittest.TestCase):
    def test_happy_path_maps_vision_payload(self) -> None:
        payload = {
            "figure_type": "bar_chart",
            "visible_text": ["accuracy", "latency"],
            "axes": ["accuracy (%)"],
            "legend_items": ["ours", "baseline"],
            "panels": [{"panel_label": "a", "panel_type": "bar_chart", "summary": "准确率对比", "confidence": "高"}],
            "direct_evidence": ["ours 柱形高于 baseline"],
            "uncertainties": [],
            "confidence": "高",
        }
        client = _FakeVisionClient(json.dumps(payload, ensure_ascii=False))
        with tempfile.TemporaryDirectory() as temp_dir:
            figure = _make_figure(Path(temp_dir))
            extractor = MultimodalFigureSemanticExtractor(vision_client=client)

            batch = extractor.extract(document=ParsedDocument(title="T"), figures=[figure])

        artifact = batch.artifacts[0]
        self.assertEqual(artifact.extraction_source, "multimodal_llm")
        self.assertEqual(artifact.figure_type, "bar_chart")
        self.assertEqual(artifact.axes, ["accuracy (%)"])
        self.assertEqual(artifact.panels[0].panel_id, "Figure 1_a")
        self.assertEqual(artifact.confidence, "高")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(len(client.calls[0]["image_paths"]), 1)

    def test_cache_hit_skips_second_call(self) -> None:
        payload = {"figure_type": "line_chart", "confidence": "中"}
        client = _FakeVisionClient(json.dumps(payload))
        with tempfile.TemporaryDirectory() as temp_dir:
            figure = _make_figure(Path(temp_dir))
            extractor = MultimodalFigureSemanticExtractor(vision_client=client)

            first = extractor.extract(document=ParsedDocument(title="T"), figures=[figure])
            second = extractor.extract(document=ParsedDocument(title="T"), figures=[figure])

            self.assertEqual(len(client.calls), 1)
            self.assertEqual(first.artifacts[0].figure_type, second.artifacts[0].figure_type)
            cache_dir = Path(temp_dir) / "semantic_cache"
            self.assertTrue(any(cache_dir.glob("*.json")))

    def test_code_fence_wrapped_json_is_accepted(self) -> None:
        client = _FakeVisionClient('```json\n{"figure_type": "result_figure", "confidence": "低"}\n```')
        with tempfile.TemporaryDirectory() as temp_dir:
            figure = _make_figure(Path(temp_dir))
            extractor = MultimodalFigureSemanticExtractor(vision_client=client)
            batch = extractor.extract(document=ParsedDocument(title="T"), figures=[figure])

        self.assertEqual(batch.artifacts[0].figure_type, "result_figure")
        self.assertEqual(batch.artifacts[0].extraction_source, "multimodal_llm")

    def test_invalid_json_falls_back_to_noop(self) -> None:
        client = _FakeVisionClient("这不是 JSON")
        with tempfile.TemporaryDirectory() as temp_dir:
            figure = _make_figure(Path(temp_dir))
            extractor = MultimodalFigureSemanticExtractor(vision_client=client)
            batch = extractor.extract(document=ParsedDocument(title="T"), figures=[figure])

        self.assertEqual(batch.artifacts[0].extraction_source, "noop")

    def test_http_error_falls_back_to_noop(self) -> None:
        class _FailingClient(_FakeVisionClient):
            def complete_with_images(self, *, prompt, image_paths):
                raise RuntimeError("HTTP 500")

        with tempfile.TemporaryDirectory() as temp_dir:
            figure = _make_figure(Path(temp_dir))
            extractor = MultimodalFigureSemanticExtractor(vision_client=_FailingClient("", ))
            batch = extractor.extract(document=ParsedDocument(title="T"), figures=[figure])

        self.assertEqual(batch.artifacts[0].extraction_source, "noop")

    def test_missing_image_files_fall_back_to_noop(self) -> None:
        client = _FakeVisionClient("{}")
        figure = FigureMetadata(
            figure_id="Figure 2",
            caption="Figure 2 shows results.",
            image_block_paths=["/nonexistent/crop.png"],
        )
        extractor = MultimodalFigureSemanticExtractor(vision_client=client)
        batch = extractor.extract(document=ParsedDocument(title="T"), figures=[figure])

        self.assertEqual(batch.artifacts[0].extraction_source, "noop")
        self.assertEqual(len(client.calls), 0)

    def test_no_vision_model_falls_back_to_noop(self) -> None:
        client = _FakeVisionClient("{}", vision_model=None)
        with tempfile.TemporaryDirectory() as temp_dir:
            figure = _make_figure(Path(temp_dir))
            extractor = MultimodalFigureSemanticExtractor(vision_client=client)
            batch = extractor.extract(document=ParsedDocument(title="T"), figures=[figure])

        self.assertEqual(batch.artifacts[0].extraction_source, "noop")
        self.assertEqual(len(client.calls), 0)

    def test_images_are_truncated_to_four(self) -> None:
        payload = {"figure_type": "unknown", "confidence": "低"}
        client = _FakeVisionClient(json.dumps(payload))
        with tempfile.TemporaryDirectory() as temp_dir:
            figure = _make_figure(Path(temp_dir), image_count=6)
            extractor = MultimodalFigureSemanticExtractor(vision_client=client)
            extractor.extract(document=ParsedDocument(title="T"), figures=[figure])

        self.assertEqual(len(client.calls[0]["image_paths"]), 4)

    def test_multi_panel_payload_maps_all_panels(self) -> None:
        payload = {
            "figure_type": "result_figure",
            "panels": [
                {"panel_label": "a", "panel_type": "bar_chart", "summary": "准确率对比", "confidence": "高"},
                {"panel_label": "b", "panel_type": "line_chart", "summary": "延迟趋势", "confidence": "中"},
                {"panel_label": "c", "panel_type": "table_like_figure", "summary": "消融表格", "confidence": "低"},
            ],
            "confidence": "中",
        }
        client = _FakeVisionClient(json.dumps(payload, ensure_ascii=False))
        with tempfile.TemporaryDirectory() as temp_dir:
            figure = _make_figure(Path(temp_dir))
            extractor = MultimodalFigureSemanticExtractor(vision_client=client)
            batch = extractor.extract(document=ParsedDocument(title="T"), figures=[figure])

        panels = batch.artifacts[0].panels
        self.assertEqual(len(panels), 3)
        self.assertEqual([panel.panel_id for panel in panels], ["Figure 1_a", "Figure 1_b", "Figure 1_c"])
        self.assertEqual(panels[1].panel_type, "line_chart")
        self.assertEqual(panels[2].confidence, "低")

    def test_table_figure_type_passes_through(self) -> None:
        payload = {
            "figure_type": "table_like_figure",
            "visible_text": ["Model", "Accuracy", "ours 95%"],
            "direct_evidence": ["表格第三行显示 ours 达到 95%"],
            "confidence": "高",
        }
        client = _FakeVisionClient(json.dumps(payload, ensure_ascii=False))
        with tempfile.TemporaryDirectory() as temp_dir:
            figure = _make_figure(Path(temp_dir))
            extractor = MultimodalFigureSemanticExtractor(vision_client=client)
            batch = extractor.extract(document=ParsedDocument(title="T"), figures=[figure])

        artifact = batch.artifacts[0]
        self.assertEqual(artifact.figure_type, "table_like_figure")
        self.assertIn("ours 95%", artifact.visible_text)

    def test_noop_infers_table_figure_type_from_caption(self) -> None:
        extractor = NoopFigureSemanticExtractor()
        batch = extractor.extract(
            document=ParsedDocument(title="T"),
            figures=[FigureMetadata(figure_id="Table 1", caption="Table 1: ablation results.")],
        )

        self.assertEqual(batch.artifacts[0].figure_type, "table_like_figure")


if __name__ == "__main__":
    unittest.main()
