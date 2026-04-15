import unittest

from paper_analysis.domain.enums import AnalysisMode
from paper_analysis.domain.schemas import FileAnalysisRequest


class FileAnalysisRequestTest(unittest.TestCase):
    def test_defaults_to_research_paper_mode(self) -> None:
        request = FileAnalysisRequest(
            input_path="input/sample.txt",
            output_markdown_path="output/report.md",
            output_json_path="output/report.json",
        )

        self.assertEqual(request.mode, AnalysisMode.RESEARCH_PAPER)


if __name__ == "__main__":
    unittest.main()
