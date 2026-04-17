import unittest

from paper_analysis.domain.enums import AnalysisMode
from paper_analysis.domain.models import FigureEvidenceBatch, FigureSemanticArtifactBatch
from paper_analysis.domain.schemas import FileAnalysisRequest


class FileAnalysisRequestTest(unittest.TestCase):
    def test_defaults_to_research_paper_mode(self) -> None:
        request = FileAnalysisRequest(
            input_path="input/sample.txt",
            output_markdown_path="output/report.md",
            output_json_path="output/report.json",
        )

        self.assertEqual(request.mode, AnalysisMode.RESEARCH_PAPER)

    def test_figure_semantic_and_evidence_batches_have_expected_defaults(self) -> None:
        semantic_batch = FigureSemanticArtifactBatch.model_validate({"artifacts": [{"figure_id": "Figure 1"}]})
        evidence_batch = FigureEvidenceBatch.model_validate({"evidences": [{"figure_id": "Figure 1"}]})

        self.assertEqual(semantic_batch.artifacts[0].figure_id, "Figure 1")
        self.assertEqual(semantic_batch.artifacts[0].confidence, "不足以判断")
        self.assertEqual(evidence_batch.evidences[0].figure_id, "Figure 1")
        self.assertEqual(evidence_batch.evidences[0].evidence_quality, "不足以判断")


if __name__ == "__main__":
    unittest.main()
