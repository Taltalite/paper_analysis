from __future__ import annotations

import unittest

from paper_analysis.domain.models import FactCheckBatch, FactCheckItem
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.crews.research.fact_check import CrewAIFactCheckRunner
from paper_analysis.runtime.pipelines.research_paper_report import ResearchPaperReportRenderer
from paper_analysis.runtime.pipelines.general_text import GeneralTextPipeline

SOURCE = "The measured accuracy of Model A is 94 percent on Dataset X."


def document() -> ParsedDocument:
    return ParsedDocument(raw_text=SOURCE, sections={"results": SOURCE},
                          metadata={"evidence_map": {"sections": {"results": "S1"}}})


def result(count: int = 1, *, summary: str = "结论1") -> AnalysisResult:
    return AnalysisResult(summary=summary, structured_data={"claims": [
        {"claim_id": f"C{i}", "statement": f"结论{i}", "evidence_ids": ["S1"], "evidence": [SOURCE]}
        for i in range(1, count + 1)
    ]})


def check(index: int = 1, **updates: object) -> FactCheckItem:
    values = dict(claim_id=f"C{index}", claim=f"结论{index}", verdict="supported", evidence_ids=["S1"], evidence_refs=[SOURCE])
    values.update(updates)
    return FactCheckItem.model_validate(values)


def render(value: AnalysisResult, checks: list[FactCheckItem], source: ParsedDocument | None = None) -> str:
    return ResearchPaperReportRenderer().render(
        source_document=source or document(), result=value, selected_sections=[],
        figure_evidence=[], figure_analyses=[], fact_checks=FactCheckBatch(checks=checks),
    )


class QualityGateTest(unittest.TestCase):
    def test_supported_claim_and_unbound_summary_are_separated_in_final_output(self) -> None:
        value = result(summary="该模型治愈所有疾病。")
        report = render(value, [check()])
        formal, draft = report.split("## 附录：", 1)
        self.assertNotIn("治愈所有疾病", formal)
        self.assertIn("治愈所有疾病", draft)
        self.assertEqual(value.summary, "结论1")
        self.assertEqual(value.quality.accepted_claim_ids, ["C1"])
        self.assertEqual(value.quality.status, "needs_review")
        first = value.model_dump()
        self.assertEqual(render(value, [check()]), report)
        self.assertEqual(value.model_dump(), first)  # 重复渲染不遗失草稿，也不套娃。
        clean = result()
        render(clean, [check(evidence_refs=[f'results: "{SOURCE}"'])])
        self.assertEqual(clean.quality.status, "passed")
        changed = document()
        changed.sections['results'] += ' The evidence has changed.'
        render(clean, [check()], changed)
        self.assertEqual(clean.quality.status, 'blocked')
        self.assertIn('source_changed', [item.code for item in clean.quality.issues])
        render(clean, [check()], changed)
        self.assertEqual(clean.quality.status, 'blocked')

    def test_missing_duplicate_unknown_and_unbound_ids_are_not_accepted(self) -> None:
        value = result(3)
        render(value, [check(), check(2), check(2), check(99)])
        self.assertEqual(value.quality.accepted_claim_ids, ["C1"])
        codes = {item.code for item in value.quality.issues}
        self.assertTrue({"missing_check", "duplicate_check", "unknown_check"}.issubset(codes))
        self.assertAlmostEqual(value.quality.coverage, 1 / 3)

    def test_supported_label_cannot_override_invalid_evidence_or_changed_claim(self) -> None:
        for update in (
            {"evidence_ids": ["S999"]}, {"claim": "与原主张不同的结论"},
            {"verdict": "partially_supported"}, {"evidence_ids": []},
        ):
            with self.subTest(update=update):
                value = result()
                render(value, [check(**update)])
                self.assertEqual(value.quality.status, "blocked")
                self.assertEqual(value.quality.accepted_claim_ids, [])
        value = result()
        value.structured_data['claims'][0]['evidence'] = ['This quotation is absent from the source.']
        render(value, [check(evidence_refs=['results'])])
        self.assertIn('unlocated_evidence', [item.code for item in value.quality.issues])

    def test_claim_inventory_normalization_and_budget_coverage(self) -> None:
        malformed = result()
        malformed.structured_data['claims'][0]['evidence'] = SOURCE
        malformed.structured_data = GeneralTextPipeline._normalize_paper_structured_data(malformed.structured_data)
        collected = CrewAIFactCheckRunner._collect_claims(analysis_result=malformed, figure_analyses=[])
        self.assertEqual(collected[0].claim_id, 'C1')
        self.assertEqual(collected[0].evidence, [SOURCE])
        value = result(21)
        self.assertEqual(len(CrewAIFactCheckRunner._collect_claims(analysis_result=value, figure_analyses=[])), 20)
        render(value, [check(i) for i in range(1, 21)])
        self.assertEqual(value.quality.expected_claims, 21)
        self.assertEqual(value.quality.checked_claims, 20)
        self.assertNotIn('C21', value.quality.accepted_claim_ids)
        self.assertEqual(value.quality.status, 'needs_review')
