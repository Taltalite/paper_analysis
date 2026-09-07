from __future__ import annotations

import asyncio
import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import fitz

from paper_analysis.adapters.llm.openai_compatible import OpenAICompatibleLLM
from paper_analysis.adapters.parser.multimodal_figure_semantics import MultimodalFigureSemanticExtractor
from paper_analysis.adapters.parser.pdf import PdfParser
from paper_analysis.domain.models import FigureMetadata
from paper_analysis.domain.schemas import ParsedDocument
from paper_analysis.runtime.crews.research.figure_analysis import CrewAIFigureAnalysisRunner
from paper_analysis.runtime.crews.research.figure_evidence_curator import DeterministicFigureEvidenceCurator
from paper_analysis.runtime.pipelines.research_paper import ResearchPaperPipeline
from paper_analysis.runtime.pipelines.research_paper_report import ResearchPaperReportRenderer


class MultimodalContractTest(unittest.TestCase):
    def test_caption_on_next_page_includes_actual_figure_page(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "split.pdf"
            with fitz.open() as pdf:
                page = pdf.new_page()
                page.draw_rect(fitz.Rect(50, 100, 500, 500), fill=(0, 0, 1))
                page.insert_text((80, 90), "Visual panel A")
                caption_page = pdf.new_page()
                caption_page.insert_text((60, 80), "Figure 4: Multi-panel experimental results.")
                pdf.save(path)
            document = asyncio.run(PdfParser().parse(path))
            figure = next(f for f in document.figures if f.figure_id == "Figure 4")
            self.assertEqual(figure.page_number, 2)
            self.assertEqual(len(figure.context_page_snapshot_paths), 1)
            paths = MultimodalFigureSemanticExtractor._resolve_image_paths(figure)
            self.assertEqual([p.name for p in paths], ["page_1.png", "page_2.png"])

    def test_vector_pdf_pixels_and_semantics_reach_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "vector.pdf"
            with fitz.open() as pdf:
                page = pdf.new_page()
                page.insert_text((70, 70), "Visual Test Paper", fontsize=18)
                page.draw_rect(fitz.Rect(100, 180, 170, 320), fill=(1, 0, 0))
                page.insert_text((110, 170), "73")
                page.insert_text((70, 360), "Figure 1: Comparison chart.")
                pdf.save(pdf_path)
            document = asyncio.run(PdfParser().parse(pdf_path))
            self.assertTrue(document.figures)
            figure = document.figures[0]
            self.assertEqual(figure.image_block_paths, [])  # 纯矢量图没有嵌入位图。
            payload = {
                "figure_type": "bar_chart", "visible_text": ["73"],
                "legend_items": ["Method A"], "axes": ["Score"],
                "panels": [{"panel_label": "a", "summary": "红色柱形", "visible_text": ["73"]}],
                "direct_evidence": ["红色柱顶标记为 73"], "confidence": "高",
            }
            response = Mock()
            response.json.return_value = {"choices": [{"message": {"content": json.dumps(payload)}}]}
            client = OpenAICompatibleLLM(model="text", vision_model="vision", base_url="https://example.com/v1")
            with patch("paper_analysis.adapters.llm.openai_compatible.httpx.post", return_value=response) as post:
                batch = MultimodalFigureSemanticExtractor(vision_client=client).extract(document=document, figures=[figure])
            content = post.call_args.kwargs["json"]["messages"][0]["content"]
            encoded = content[1]["image_url"]["url"].split(",", 1)[1]
            self.assertEqual(base64.b64decode(encoded), Path(figure.page_snapshot_path).read_bytes())
            evidence = DeterministicFigureEvidenceCurator().run(document=document, figures=[figure], semantic_artifacts=batch)
            cleaned = CrewAIFigureAnalysisRunner._sanitize_batch(evidence)
            prompt = CrewAIFigureAnalysisRunner._build_task_description(document=document, evidence_batch=cleaned)
            report = ResearchPaperReportRenderer._render_figure_evidence_section(cleaned.evidences)
            for text in ("73", "Method A", "红色柱形"):
                self.assertIn(text, prompt)
                self.assertIn(text, report)
            self.assertEqual(cleaned.evidences[0].panels[0].visible_text, ["73"])
            self.assertIn("已调用多模态模型", report)

    def test_snapshot_precedes_partial_images_and_missing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "page.png"
            snapshot.write_bytes(b"page")
            fragment = Path(directory) / "fragment.png"
            fragment.write_bytes(b"fragment")
            figure = FigureMetadata(page_snapshot_path=str(snapshot), image_block_paths=[str(fragment)])
            self.assertEqual(MultimodalFigureSemanticExtractor._resolve_image_paths(figure), [snapshot])
            figure.image_block_paths = ["/missing/fragment.png"]
            self.assertEqual(MultimodalFigureSemanticExtractor._resolve_image_paths(figure), [snapshot])

    def test_changed_reference_invalidates_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "images" / "chart.png"
            image.parent.mkdir()
            image.write_bytes(b"fixture")
            client = Mock(vision_model="vision")
            client.complete_with_images.return_value = '{"figure_type":"bar_chart","visible_text":["73"]}'
            extractor = MultimodalFigureSemanticExtractor(vision_client=client)
            figure = FigureMetadata(figure_id="Figure 1", image_block_paths=[str(image)])
            for references in (["original"], ["original"], ["changed"]):
                figure.referenced_text_spans = references
                extractor.extract(document=ParsedDocument(), figures=[figure])
            self.assertEqual(client.complete_with_images.call_count, 2)

    def test_invalid_payload_is_not_cached_and_failure_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "images" / "chart.png"
            image.parent.mkdir()
            image.write_bytes(b"fixture")
            client = Mock(vision_model="vision")
            client.complete_with_images.return_value = '{}'
            extractor = MultimodalFigureSemanticExtractor(vision_client=client)
            figure = FigureMetadata(figure_id="Figure 1", image_block_paths=[str(image)])
            for _ in range(2):
                batch = extractor.extract(document=ParsedDocument(), figures=[figure])
            self.assertEqual(client.complete_with_images.call_count, 2)
            self.assertEqual(batch.artifacts[0].extraction_source, "noop")
            self.assertEqual(batch.artifacts[0].visible_text, [])
            self.assertEqual(batch.artifacts[0].confidence, "低")
            self.assertIn("ValidationError", batch.artifacts[0].uncertainties[0])
            self.assertFalse(list(Path(directory).glob("semantic_cache/*.json")))
            evidence = DeterministicFigureEvidenceCurator().run(document=ParsedDocument(), figures=[figure], semantic_artifacts=batch)
            report = ResearchPaperReportRenderer._render_figure_evidence_section(evidence.evidences)
            self.assertIn("未完成视觉识别", report)
            self.assertIn("ValidationError", report)

    def test_structure_repair_preserves_only_parser_owned_assets(self) -> None:
        originals = [
            FigureMetadata(figure_id="Figure 1", page_number=2, page_snapshot_path="page2.png"),
            FigureMetadata(figure_id="Figure 2", page_number=3, image_block_paths=["chart2.png"]),
        ]
        refined = [
            FigureMetadata(figure_id="Fig. 1", caption="修复图注", image_block_paths=["invented.png"]),
            FigureMetadata(figure_id="Figure 3", page_snapshot_path="invented-page.png"),
        ]
        figures = ResearchPaperPipeline._restore_figure_assets(originals, refined)
        self.assertEqual(figures[0].page_snapshot_path, "page2.png")
        self.assertEqual(figures[0].image_block_paths, [])
        self.assertEqual(figures[0].caption, "修复图注")
        self.assertIsNone(figures[1].page_snapshot_path)
        self.assertEqual(figures[2].image_block_paths, ["chart2.png"])

    def test_replaced_pdf_regenerates_page_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "same.pdf"
            parser = PdfParser()
            pixels = []
            for color in ((1, 0, 0), (0, 0, 1)):
                with fitz.open() as pdf:
                    page = pdf.new_page()
                    page.draw_rect(fitz.Rect(50, 50, 200, 200), fill=color)
                    path = parser._save_page_snapshot(document=pdf, source_path=source, page_number=1)
                    pixels.append(Path(path).read_bytes())
            self.assertNotEqual(pixels[0], pixels[1])
