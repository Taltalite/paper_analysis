import asyncio
import unittest
from pathlib import Path

from paper_analysis.adapters.parser.pdf import PdfParser


class PdfParserTest(unittest.TestCase):
    def test_parse_template_pdf_to_structured_document(self) -> None:
        parsed = asyncio.run(PdfParser().parse(Path("input/template.pdf")))

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
        self.assertTrue(parsed.figures[0].referenced_text_spans)
        self.assertIn("# PDF 结构化解析", parsed.markdown)
        self.assertIn("## 图表元数据", parsed.markdown)
        self.assertIn("## 摘要（Abstract）", parsed.markdown)


if __name__ == "__main__":
    unittest.main()
