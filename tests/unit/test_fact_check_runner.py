import unittest

from paper_analysis.domain.models import FigureAnalysis
from paper_analysis.domain.schemas import AnalysisResult
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


if __name__ == "__main__":
    unittest.main()
