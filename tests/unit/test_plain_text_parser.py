import asyncio
import tempfile
import unittest
from pathlib import Path

from paper_analysis.adapters.parser.plain_text import PlainTextParser


class PlainTextParserTest(unittest.TestCase):
    def test_parse_reads_text_and_infers_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.md"
            path.write_text("Example Title\n\nSecond line.", encoding="utf-8")

            parsed = asyncio.run(PlainTextParser().parse(path))

        self.assertEqual(parsed.title, "Example Title")
        self.assertIn("Second line.", parsed.raw_text)
        self.assertEqual(parsed.markdown, parsed.raw_text)


if __name__ == "__main__":
    unittest.main()
