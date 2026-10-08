import unittest

from paper_analysis.adapters.parser.mcp_figure_semantics import NoopFigureSemanticExtractor
from paper_analysis.domain.models import ClaimEvidence, FactCheckBatch, FigureMetadata, FigureEvidence
from paper_analysis.domain.quality import QualityReport
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.domain.qa import QuestionRequest
from paper_analysis.runtime.pipelines.research_products import build_research_products
from paper_analysis.runtime.pipelines.research_paper_report import ResearchPaperReportRenderer
from paper_analysis.runtime.pipelines.question_answer import QuestionAnswerPipeline
from test_question_answer import FakeRunner, FakeChecker, document


class DeliveryRegressions(unittest.TestCase):
    def test_uncertainties_do_not_release_model_assertions(self):
        class Runner(FakeRunner):
            def run(self, **kwargs):
                draft = super().run(**kwargs)
                draft.uncertainties = ["FAKE_LABEL_999"]
                return draft
        answer = QuestionAnswerPipeline(runner=Runner(), checker=FakeChecker(), vision=NoopFigureSemanticExtractor()).run(
            document=document(), request=QuestionRequest(question="重复数？", max_followups=0))
        self.assertNotIn("FAKE_LABEL_999", answer.model_dump_json())

    def test_blocked_claim_and_invented_benchmark_not_in_delivery(self):
        doc = ParsedDocument(title="synthetic", metadata={"ordered_blocks": [
            {"block_id": "b1", "page_number": 1, "text": "No benchmark reported in this source."}]})
        result = AnalysisResult(structured_data={"claims": [ClaimEvidence(claim_id="c1", statement="BAD_RESULT_999",
            evidence_ids=["b1"]).model_dump()], "benchmark": {"status": "available", "entries": [{
            "method": "Invented", "metric": "Accuracy", "value_raw": "99.9", "value": 99.9,
            "value_source": "explicit", "evidence_ids": ["missing"]}]}})
        text = ResearchPaperReportRenderer().render(source_document=doc, result=result,
            selected_sections=[], figure_evidence=[], figure_analyses=[], fact_checks=FactCheckBatch())
        delivery = text.split("## 附录")[0]
        self.assertNotIn("BAD_RESULT_999", delivery)
        self.assertNotIn("Invented", delivery)
        self.assertEqual(result.research_products.benchmark.status, "not_reported")

    def test_section_ids_experiments_story_and_benchmark_are_bound(self):
        statement = "MethodA accuracy 0.91 on dataset B with three replicates."
        doc = ParsedDocument(sections={"results": statement}, section_order=["results"],
            metadata={"document_sha256": "s", "evidence_map": {"sections": {"results": "S1"}}})
        claim = ClaimEvidence(claim_id="c1", statement=statement, evidence=[statement], evidence_ids=["S1"],
            story_role="design", experiment={"replicates": "three replicates", "controls": "invented control"})
        result = AnalysisResult(structured_data={"claims": [claim.model_dump()], "benchmark": {"status": "available", "entries": [{
            "method": "MethodA", "metric": "accuracy", "value_raw": "0.91", "value": 0.91,
            "value_source": "explicit", "evidence_ids": ["S1"], "claim_ids": ["c1"]}]}},
            quality=QualityReport(accepted_claim_ids=["c1"]))
        products = build_research_products(document=doc, result=result, figure_evidence=[], figure_analyses=[])
        self.assertEqual(products.findings[0].evidence_ids, ["S1"])
        self.assertEqual(products.story.nodes[0].role, "design")
        self.assertEqual(products.evidence_matrix[0].replicates, "three replicates")
        self.assertEqual(products.evidence_matrix[0].controls, "not_reported")
        self.assertEqual(products.benchmark.entries[0].value, 0.91)

    def test_reading_figure_is_not_verification(self):
        doc = ParsedDocument(figures=[FigureMetadata(figure_id="Figure 1", caption="data", page_number=1)])
        products = build_research_products(document=doc, result=AnalysisResult(), figure_evidence=[
            FigureEvidence(figure_id="Figure 1", semantic_source="multimodal_llm", direct_evidence=["observation"])], figure_analyses=[])
        self.assertEqual(products.coverage.verified.figures, [])
