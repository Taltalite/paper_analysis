import asyncio
import unittest

from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.pipelines.general_text import GeneralTextPipeline
from paper_analysis.runtime.pipelines.profiles import GENERAL_TEXT_PROFILE, RESEARCH_PAPER_PROFILE


class FakeCrewRunner:
    def __init__(self, result: AnalysisResult) -> None:
        self._result = result

    def run(self, *, document: ParsedDocument, profile) -> AnalysisResult:  # noqa: ANN001
        return self._result


class GeneralTextPipelineTest(unittest.TestCase):
    def test_builds_generic_markdown_when_structured_data_is_generic(self) -> None:
        pipeline = GeneralTextPipeline(
            profile=GENERAL_TEXT_PROFILE,
            crew_runner=FakeCrewRunner(
                AnalysisResult(
                    summary="Generic summary",
                    key_points=["Point A", "Point B"],
                    limitations=["Limitation A"],
                    structured_data={"sections": {"overview": "Grounded overview"}},
                )
            ),
        )

        result = asyncio.run(
            pipeline.run(ParsedDocument(title="Document Title", raw_text="Body text"))
        )

        self.assertEqual(result.title, "Document Title")
        self.assertIn("# 通用文本分析报告", result.markdown_report)
        self.assertIn("Grounded overview", result.markdown_report)

    def test_builds_paper_markdown_when_structured_data_matches_paper_shape(self) -> None:
        pipeline = GeneralTextPipeline(
            profile=RESEARCH_PAPER_PROFILE,
            crew_runner=FakeCrewRunner(
                AnalysisResult(
                    summary="Paper summary",
                    structured_data={
                        "metadata": {
                            "title": "Paper Title",
                            "authors": ["Author One"],
                            "venue": "TestConf",
                            "year": "2025",
                        },
                        "extracted_notes": {
                            "research_problem": "Problem",
                            "core_method": "Method",
                            "datasets": ["Dataset A"],
                            "experimental_setup": "Setup",
                            "main_results": "Results",
                        },
                        "novelty": "Novelty",
                        "strengths": ["Strong point"],
                        "limitations": ["Weak point"],
                        "reproducibility": "Medium",
                    },
                )
            ),
        )

        result = asyncio.run(
            pipeline.run(ParsedDocument(title="Paper Title", raw_text="Body text"))
        )

        self.assertIn("# 论文分析报告", result.markdown_report)
        self.assertIn("## 研究问题", result.markdown_report)
        self.assertIn("Strong point", result.markdown_report)


if __name__ == "__main__":
    unittest.main()
