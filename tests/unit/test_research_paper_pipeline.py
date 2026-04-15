import asyncio
import unittest

from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.pipelines.research_paper import ResearchPaperPipeline


class RecordingCrewRunner:
    def __init__(self, result: AnalysisResult) -> None:
        self._result = result
        self.received_document: ParsedDocument | None = None

    def run(self, *, document: ParsedDocument, profile) -> AnalysisResult:  # noqa: ANN001
        self.received_document = document
        return self._result


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
                    "interview_pitch": "Pitch",
                },
            )
        )
        pipeline = ResearchPaperPipeline(crew_runner=runner)
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
            metadata={"parser_kind": "pdf", "page_count": 2, "doi": "10.1000/test"},
        )

        result = asyncio.run(pipeline.run(document))

        self.assertIsNotNone(runner.received_document)
        assert runner.received_document is not None
        self.assertIn("## Abstract", runner.received_document.raw_text)
        self.assertNotIn("RAW RAW RAW RAW RAW", runner.received_document.raw_text)
        self.assertIn("# Research Paper Analysis Report", result.markdown_report)
        self.assertIn("## Structured Parse Preview", result.markdown_report)
        self.assertIn("selected_sections", result.structured_data)


if __name__ == "__main__":
    unittest.main()
