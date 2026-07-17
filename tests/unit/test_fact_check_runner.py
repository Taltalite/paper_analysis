import unittest

from paper_analysis.domain.models import FigureAnalysis
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.crews.research.fact_check import CrewAIFactCheckRunner


class FactCheckRunnerTest(unittest.TestCase):
    def test_collects_structured_and_figure_claims(self) -> None:
        claims = CrewAIFactCheckRunner._collect_claims(
            analysis_result=AnalysisResult(
                structured_data={
                    "claims": [
                        {
                            "claim_id": "method-1",
                            "statement": "方法使用两阶段训练。",
                            "category": "method",
                            "source_sections": ["method"],
                            "evidence": ["The model is trained in two stages."],
                        }
                    ]
                }
            ),
            figure_analyses=[
                FigureAnalysis(
                    figure_id="Figure 1",
                    claimed_conclusion="作者声称该方法获得更高准确率。",
                    main_observations=["曲线高于基线。"],
                    confidence="中",
                )
            ],
        )

        self.assertEqual(len(claims), 2)
        self.assertEqual(claims[0].claim_id, "method-1")
        self.assertEqual(claims[1].category, "figure_claim")
        self.assertEqual(claims[1].evidence_ids, ["Figure 1"])

    def test_fallback_marks_claims_unverifiable(self) -> None:
        claims = CrewAIFactCheckRunner._collect_claims(
            analysis_result=AnalysisResult(summary="Summary claim"),
            figure_analyses=[],
        )

        batch = CrewAIFactCheckRunner._fallback_batch(
            claims=claims,
            reason="test fallback",
        )

        self.assertEqual(batch.checks[0].verdict, "unverifiable")
        self.assertIn("test fallback", batch.overall_assessment)

    def test_run_without_llm_includes_rule_flags(self) -> None:
        runner = CrewAIFactCheckRunner(llm_client=None)
        document = ParsedDocument(
            title="Test",
            raw_text="The pipeline reaches 95% accuracy in our experiments.",
            sections={"results": "The pipeline reaches 95% accuracy in our experiments."},
        )
        analysis_result = AnalysisResult(
            structured_data={
                "claims": [
                    {
                        "claim_id": "text-1",
                        "statement": "The pipeline reaches 99% accuracy.",
                    }
                ]
            }
        )

        batch = runner.run(
            document=document,
            analysis_result=analysis_result,
            figure_analyses=[],
            figure_evidence=[],
        )

        self.assertEqual(batch.checks[0].verdict, "unverifiable")
        self.assertTrue(any("未引用 evidence ID" in flag for flag in batch.rule_flags))
        self.assertTrue(any("99%" in flag for flag in batch.rule_flags))

    def test_conflicting_number_flagged_via_figure_evidence(self) -> None:
        runner = CrewAIFactCheckRunner(llm_client=None)
        document = ParsedDocument(
            title="Test",
            raw_text="See Figure 1 for the comparison.",
            sections={"results": "See Figure 1 for the comparison."},
        )
        analysis_result = AnalysisResult(summary="Summary claim")

        batch = runner.run(
            document=document,
            analysis_result=analysis_result,
            figure_analyses=[
                FigureAnalysis(
                    figure_id="Figure 1",
                    claimed_conclusion="作者声称准确率达到 88%。",
                    main_observations=["曲线高于基线。"],
                    confidence="中",
                )
            ],
            figure_evidence=[],
        )

        figure_check = [check for check in batch.checks if check.claim_source == "figure"]
        self.assertTrue(figure_check)
        self.assertEqual(figure_check[0].evidence_ids, ["Figure 1"])
        self.assertTrue(any("88%" in flag for flag in batch.rule_flags))


if __name__ == "__main__":
    unittest.main()
