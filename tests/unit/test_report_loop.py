import asyncio
import tempfile
import unittest
from pathlib import Path

from paper_analysis.domain.execution import ExecutionPolicyRequest, ResolvedPolicy
from paper_analysis.domain.models import ClaimEvidence, FactCheckBatch, FactCheckItem, FigureMetadata, FigureEvidence
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.pipelines.research_paper import ResearchPaperPipeline
from paper_analysis.runtime.pipelines.report_visual_review import review_report_visuals


class ReportLoopTests(unittest.TestCase):
    def test_no_new_evidence_stops_without_extra_generation(self):
        class Runner:
            calls = 0
            def run(self, **kwargs):
                self.calls += 1
                return AnalysisResult(summary="未核验", structured_data={"claims": [ClaimEvidence(
                    claim_id="c1", statement="unverified", evidence_ids=["S1"]).model_dump()]})
        runner = Runner()
        pipeline = ResearchPaperPipeline(crew_runner=runner)
        document = ParsedDocument(raw_text="original", sections={"results": "original"}, section_order=["results"])
        result = asyncio.run(pipeline.run(document, policy=ResolvedPolicy.resolve(ExecutionPolicyRequest(report_followups=2))))
        self.assertEqual(runner.calls, 1)
        self.assertEqual(result.structured_data["execution_stop_reason"], "no_new_evidence")
        self.assertFalse(result.quality.accepted_claim_ids)

    def test_report_visual_claim_is_blocked_without_direct_review(self):
        claim = ClaimEvidence(claim_id="v1", statement="visual assertion", evidence_ids=["Figure 1"])
        result = AnalysisResult(structured_data={"claims": [claim.model_dump()]})
        checks = FactCheckBatch(checks=[FactCheckItem(claim_id="v1", claim=claim.statement,
            verdict="supported", evidence_ids=["Figure 1"])])
        review_report_visuals(document=ParsedDocument(figures=[FigureMetadata(figure_id="Figure 1", caption="synthetic")]),
            result=result, analyses=[], evidence=[FigureEvidence(figure_id="Figure 1", semantic_source="multimodal_llm")],
            checks=checks, session=None)
        self.assertEqual(checks.checks[0].verdict, "unverifiable")
        self.assertEqual(result.structured_data["visually_reviewed_figures"], [])
