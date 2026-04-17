import unittest

from paper_analysis.adapters.parser.mcp_figure_semantics import NoopFigureSemanticExtractor
from paper_analysis.domain.models import FigureMetadata
from paper_analysis.domain.schemas import ParsedDocument


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


if __name__ == "__main__":
    unittest.main()
