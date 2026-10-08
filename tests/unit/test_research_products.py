import unittest

from paper_analysis.domain.models import ClaimEvidence, FigureAnalysis, FigureEvidence, FigureMetadata
from paper_analysis.domain.quality import QualityReport
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.pipelines.research_products import build_research_products


class ResearchProductsTests(unittest.TestCase):
    def test_products_share_claim_ids_and_expose_coverage(self) -> None:
        document = ParsedDocument(
            title="Synthetic paper",
            section_order=["abstract", "results"],
            sections={"abstract": "摘要", "results": "结果"},
            figures=[FigureMetadata(figure_id="Figure 1", caption="Figure 1. 结果", page_number=2)],
            metadata={
                "document_sha256": "doc-sha",
                "ordered_blocks": [{"block_id": "p2_b1", "page_number": 2, "text": "三个重复。"}],
            },
        )
        result = AnalysisResult(
            summary="结论",
            structured_data={"claims": [ClaimEvidence(
                claim_id="claim-1",
                statement="三个生物学重复",
                category="result",
                evidence_ids=["p2_b1"],
            ).model_dump()]},
            quality=QualityReport(accepted_claim_ids=["claim-1"], checked_claims=1, expected_claims=1),
        )
        products = build_research_products(
            document=document,
            result=result,
            figure_evidence=[FigureEvidence(
                figure_id="Figure 1",
                figure_title_or_caption="Figure 1. 结果",
                page_number=2,
                semantic_source="parser_caption",
            )],
            figure_analyses=[FigureAnalysis(figure_id="Figure 1", experiment_focus="结果")],
        )
        self.assertEqual(products.evidence[0].document_sha256, "doc-sha")
        self.assertEqual(products.coverage.verified.claims, ["claim-1"])
        self.assertEqual(products.figure_flow.nodes[0].figure, "Figure 1")
        self.assertEqual(products.benchmark.status, "not_reported")


if __name__ == "__main__":
    unittest.main()
