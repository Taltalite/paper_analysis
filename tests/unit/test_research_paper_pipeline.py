import asyncio
import unittest

from paper_analysis.domain.models import (
    DocumentStructureDraft,
    FigureAnalysis,
    FigureAnalysisBatch,
    FigureMetadata,
)
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.pipelines.research_paper import ResearchPaperPipeline


class RecordingCrewRunner:
    def __init__(self, result: AnalysisResult) -> None:
        self._result = result
        self.received_document: ParsedDocument | None = None

    def run(self, *, document: ParsedDocument, profile) -> AnalysisResult:  # noqa: ANN001
        self.received_document = document
        return self._result


class FakeFigureRunner:
    def __init__(self) -> None:
        self.received_figures: list[FigureMetadata] = []

    def run(self, *, document: ParsedDocument, figures: list[FigureMetadata]) -> FigureAnalysisBatch:  # noqa: ANN001
        self.received_figures = figures
        return FigureAnalysisBatch(
            analyses=[
                FigureAnalysis(
                    figure_id=figures[0].figure_id,
                    figure_title_or_caption=figures[0].caption,
                    experiment_focus="比较不同信息检索方案的速度与准确性表现",
                    compared_items=["proposed pipeline", "leading solutions"],
                    metrics_or_axes=["speed", "accuracy"],
                    main_observations=["Figure 1 展示端到端流程，并支撑速度与准确性提升的叙述。"],
                    claimed_conclusion="作者据此强调该方案在信息检索链路上更快且更稳健。",
                    consistency_check="caption 与正文引用基本一致，但仅凭图页无法独立验证全部实验细节。",
                    confidence="中",
                )
            ]
        )


class FakeStructuringRunner:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, *, document: ParsedDocument) -> DocumentStructureDraft:  # noqa: ANN001
        self.calls += 1
        return DocumentStructureDraft(
            title="Refined Paper Title",
            authors=["Author A", "Author B"],
            doi="10.1000/test",
            venue="Venue",
            year="2025",
            abstract="Refined abstract",
            sections={
                "abstract": "Refined abstract",
                "introduction": "Refined introduction",
                "method": "Refined method",
                "experimental_setup": "Refined experimental setup",
                "results": "Refined results",
                "conclusion": "Refined conclusion",
            },
            section_order=[
                "abstract",
                "introduction",
                "method",
                "experimental_setup",
                "results",
                "conclusion",
            ],
            figures=document.figures,
        )


class ResearchPaperPipelineTest(unittest.TestCase):
    def test_focuses_on_selected_sections_and_builds_research_report(self) -> None:
        runner = RecordingCrewRunner(
            AnalysisResult(
                summary="Short summary",
                structured_data={
                    "metadata": {
                        "title": "Template Paper",
                        "authors": ["Author A"],
                        "venue": "Venue",
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
                    "strengths": ["Strength A"],
                    "limitations": ["Limitation A"],
                    "reproducibility": "Medium",
                },
            )
        )
        structuring_runner = FakeStructuringRunner()
        figure_runner = FakeFigureRunner()
        pipeline = ResearchPaperPipeline(
            crew_runner=runner,
            structuring_runner=structuring_runner,
            figure_runner=figure_runner,
        )
        document = ParsedDocument(
            title="Template Paper",
            raw_text="RAW " * 5000,
            markdown="# Parsed PDF Structure\n",
            sections={
                "abstract": "Abstract section text.",
                "introduction": "Introduction section text.",
                "method": "Method section text.",
                "experimental_setup": "Experimental section text.",
                "results": "Results section text.",
            },
            section_order=["abstract", "introduction", "method", "experimental_setup", "results"],
            figures=[
                FigureMetadata(
                    figure_id="Figure 1",
                    caption="Fig. 1 | End-to-end solution for DNA information retrieval.",
                    page_number=2,
                    referenced_text_spans=["As shown in Fig. 1, the pipeline integrates multiple stages."],
                )
            ],
            metadata={
                "parser_kind": "pdf",
                "page_count": 2,
                "doi": "10.1000/test",
                "ordered_blocks": [],
                "coarse_structure": {"title": "Template Paper"},
            },
        )

        result = asyncio.run(pipeline.run(document))

        self.assertIsNotNone(runner.received_document)
        assert runner.received_document is not None
        self.assertIn("## Abstract", runner.received_document.raw_text)
        self.assertIn("Refined method", runner.received_document.raw_text)
        self.assertNotIn("RAW RAW RAW RAW RAW", runner.received_document.raw_text)
        self.assertEqual(structuring_runner.calls, 1)
        self.assertEqual(len(figure_runner.received_figures), 1)
        self.assertIn("# 研究型文献分析报告", result.markdown_report)
        self.assertIn("## 图像实验结果分析", result.markdown_report)
        self.assertIn("## 图文一致性检查", result.markdown_report)
        self.assertIn("figure_analyses", result.structured_data)
        self.assertIn("## 结构化解析预览", result.markdown_report)
        self.assertIn("selected_sections", result.structured_data)


if __name__ == "__main__":
    unittest.main()
