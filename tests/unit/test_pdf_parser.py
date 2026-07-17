import asyncio
import base64
import tempfile
import unittest
from pathlib import Path

import fitz

from paper_analysis.adapters.parser.pdf import PdfParser

_ONE_PX_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _build_template_pdf(path: Path) -> None:
    document = fitz.open()
    try:
        page_one = document.new_page()
        page_one.insert_text(
            fitz.Point(72, 90),
            "Scalable and robust DNA-based storage",
            fontsize=16,
        )
        page_one.insert_text(fitz.Point(72, 130), "Abstract", fontsize=13)
        page_one.insert_textbox(
            fitz.Rect(72, 140, 540, 260),
            "DNA-based storage is emerging as a durable medium for archival data. "
            "This work presents a scalable and robust encoding pipeline that combines "
            "synthetic-modular blocks with error-correcting codes to tolerate high-noise channels.",
            fontsize=10.5,
        )
        page_one.insert_text(fitz.Point(72, 280), "Methods", fontsize=13)
        page_one.insert_textbox(
            fitz.Rect(72, 290, 540, 470),
            "We combine a modular synthesis approach with an error-correcting neural decoder. "
            "The pipeline first partitions payloads into synthetic blocks, then applies layered "
            "redundancy so that the neural decoder can recover reads from noisy sequencing data.",
            fontsize=10.5,
        )

        page_two = document.new_page()
        page_two.insert_text(fitz.Point(72, 80), "Results", fontsize=13)
        page_two.insert_textbox(
            fitz.Rect(72, 90, 540, 180),
            "As shown in Figure 1, the proposed pipeline achieves robust recovery with 95% accuracy "
            "under high-noise conditions, an improvement over the evaluated baselines.",
            fontsize=10.5,
        )
        page_two.insert_image(fitz.Rect(72, 200, 312, 380), stream=_ONE_PX_PNG)
        page_two.insert_textbox(
            fitz.Rect(72, 390, 540, 430),
            "Figure 1: Overview of the DNA storage encoding pipeline with error-correcting modules.",
            fontsize=10,
        )
        page_two.insert_text(fitz.Point(72, 450), "Conclusion", fontsize=13)
        page_two.insert_textbox(
            fitz.Rect(72, 460, 540, 540),
            "These results establish a viable path toward commercial DNA-based archival storage "
            "and suggest broader applications in a broader sense.",
            fontsize=10.5,
        )
        document.save(path)
    finally:
        document.close()


class PdfParserTest(unittest.TestCase):
    def test_parse_template_pdf_to_structured_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "template.pdf"
            _build_template_pdf(pdf_path)

            parsed = asyncio.run(PdfParser().parse(pdf_path))

        self.assertIn("Scalable and robust DNA-based storage", parsed.title)
        self.assertEqual(parsed.metadata["parser_kind"], "pdf")
        self.assertEqual(parsed.metadata["page_count"], 2)
        self.assertGreaterEqual(parsed.metadata["figure_count"], 1)
        self.assertIn("ordered_blocks", parsed.metadata)
        self.assertIn("coarse_structure", parsed.metadata)
        self.assertIn("abstract", parsed.sections)
        self.assertIn("method", parsed.sections)
        self.assertTrue(parsed.figures)
        self.assertIn("Figure 1", parsed.figures[0].figure_id)
        self.assertTrue(parsed.figures[0].caption)
        self.assertIsInstance(parsed.figures[0].image_block_paths, list)
        self.assertTrue(parsed.figures[0].referenced_text_spans)
        self.assertIn("# PDF 结构化解析", parsed.markdown)
        self.assertIn("## 图表元数据", parsed.markdown)
        self.assertIn("## 摘要（Abstract）", parsed.markdown)
        self.assertIn("## 证据索引", parsed.markdown)

        evidence_map = parsed.metadata["evidence_map"]
        self.assertEqual(evidence_map["sections"].get("abstract"), "S1")
        self.assertIn("Figure 1", evidence_map["figures"])


if __name__ == "__main__":
    unittest.main()
