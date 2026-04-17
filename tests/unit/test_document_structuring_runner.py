import unittest

from paper_analysis.domain.models import DocumentStructureDraft
from paper_analysis.runtime.crews.research.document_structuring import (
    CrewAIDocumentStructuringRunner,
)


class DocumentStructuringRunnerTest(unittest.TestCase):
    def test_parse_draft_text_allows_newlines_inside_json_strings(self) -> None:
        coarse = DocumentStructureDraft(title="Fallback")
        raw_output = """```json
{
  "title": "Real Title",
  "authors": ["Author A", "Author B"],
  "doi": "10.1126/sciadv.example",
  "venue": "Sci. Adv.",
  "year": "2025",
  "abstract": "第一行
第二行",
  "sections": {
    "introduction": "Intro text"
  },
  "section_order": ["introduction"],
  "figures": [],
  "discarded_noise": [],
  "uncertainties": []
}
```"""

        draft = CrewAIDocumentStructuringRunner._parse_draft_text(
            raw_text=raw_output,
            coarse_draft=coarse,
        )

        self.assertEqual(draft.title, "Real Title")
        self.assertEqual(draft.venue, "Sci. Adv.")
        self.assertIn("introduction", draft.sections)


if __name__ == "__main__":
    unittest.main()
