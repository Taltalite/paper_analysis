import unittest

from paper_analysis.domain.models import ClaimEvidence, FigureEvidence
from paper_analysis.domain.schemas import ParsedDocument
from paper_analysis.runtime.pipelines.fact_check_prechecks import run_fact_check_prechecks


def _document(raw_text: str) -> ParsedDocument:
    return ParsedDocument(title="Test", raw_text=raw_text)


class FactCheckPrecheckTest(unittest.TestCase):
    def test_clean_claim_produces_no_flags(self) -> None:
        document = _document("The method achieves 95% accuracy on the benchmark dataset.")
        claims = [
            ClaimEvidence(
                claim_id="text-1",
                statement="The method achieves 95% accuracy.",
                source_sections=["results"],
                evidence=["The method achieves 95% accuracy on the benchmark dataset."],
                evidence_ids=["S4"],
            )
        ]

        flags = run_fact_check_prechecks(document=document, claims=claims, figure_evidence=[])

        self.assertEqual(flags, [])

    def test_missing_evidence_reference_is_flagged(self) -> None:
        document = _document("Some raw text.")
        claims = [ClaimEvidence(claim_id="text-1", statement="Some claim.")]

        flags = run_fact_check_prechecks(document=document, claims=claims, figure_evidence=[])

        self.assertTrue(any("未引用 evidence ID" in flag for flag in flags))

    def test_fabricated_evidence_snippet_is_flagged(self) -> None:
        document = _document("Actual raw text from the paper.")
        claims = [
            ClaimEvidence(
                claim_id="text-2",
                statement="claim",
                source_sections=["abstract"],
                evidence_ids=["S1"],
                evidence=["这句话根本不在原文里，属于编造的证据片段……"],
            )
        ]

        flags = run_fact_check_prechecks(document=document, claims=claims, figure_evidence=[])

        self.assertTrue(any("证据片段未在原文中找到" in flag for flag in flags))

    def test_unknown_number_is_flagged(self) -> None:
        document = _document("Accuracy reaches 95% under high noise.")
        claims = [
            ClaimEvidence(
                claim_id="text-3",
                statement="Accuracy reaches 99% under high noise.",
                source_sections=["results"],
                evidence_ids=["S4"],
            )
        ]

        flags = run_fact_check_prechecks(document=document, claims=claims, figure_evidence=[])

        self.assertTrue(any("99%" in flag for flag in flags))

    def test_number_found_in_figure_evidence_is_not_flagged(self) -> None:
        document = _document("See Figure 2 for details.")
        figure_evidence = [
            FigureEvidence(figure_id="Figure 2", direct_evidence=["柱形图显示 accuracy 为 88%"])
        ]
        claims = [
            ClaimEvidence(
                claim_id="figure-1",
                statement="Figure 2 shows 88% accuracy.",
                source_sections=["Figure 2"],
                evidence_ids=["Figure 2"],
            )
        ]

        flags = run_fact_check_prechecks(
            document=document, claims=claims, figure_evidence=figure_evidence
        )

        self.assertEqual(flags, [])


if __name__ == "__main__":
    unittest.main()
