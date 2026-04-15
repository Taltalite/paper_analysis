import asyncio
import tempfile
import unittest
from pathlib import Path

from paper_analysis.domain.enums import AnalysisMode
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.services.analysis_service import AnalysisService


class FakeParser:
    def __init__(self, title: str) -> None:
        self.title = title
        self.paths: list[Path] = []

    async def parse(self, path: Path) -> ParsedDocument:
        self.paths.append(path)
        return ParsedDocument(title=self.title, raw_text="parsed text", markdown="parsed text")


class FakeRuntime:
    def __init__(self) -> None:
        self.calls: list[tuple[AnalysisMode, ParsedDocument]] = []

    async def run(self, mode: AnalysisMode, document: ParsedDocument) -> AnalysisResult:
        self.calls.append((mode, document))
        return AnalysisResult(title=document.title, summary="done")


class AnalysisServiceTest(unittest.TestCase):
    def test_uses_text_parser_for_txt_files_and_returns_execution_bundle(self) -> None:
        text_parser = FakeParser(title="Text Title")
        pdf_parser = FakeParser(title="PDF Title")
        runtime = FakeRuntime()
        service = AnalysisService(
            text_parser=text_parser,
            pdf_parser=pdf_parser,
            runtime=runtime,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.txt"
            path.write_text("body", encoding="utf-8")
            execution = asyncio.run(service.analyze_file(path, AnalysisMode.GENERAL_TEXT))

        self.assertEqual(execution.document.title, "Text Title")
        self.assertEqual(execution.result.summary, "done")
        self.assertEqual(len(text_parser.paths), 1)
        self.assertEqual(len(pdf_parser.paths), 0)
        self.assertEqual(runtime.calls[0][0], AnalysisMode.GENERAL_TEXT)


if __name__ == "__main__":
    unittest.main()
