from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from paper_analysis.adapters.parser.mcp_figure_semantics import NoopFigureSemanticExtractor
from paper_analysis.adapters.parser.pdf import PdfParser
from paper_analysis.domain.models import FactCheckBatch, FactCheckItem, FigureMetadata, FigurePanel, FigureSemanticArtifact, FigureSemanticArtifactBatch
from paper_analysis.domain.qa import AnswerClaim, AnswerDraft, QuestionRequest
from paper_analysis.domain.schemas import ParsedDocument
from paper_analysis.runtime.pipelines.question_answer import QuestionAnswerPipeline
from paper_analysis.services.question_answer_service import QuestionAnswerService

QUOTE = "Three biological replicates were used for ATAC-seq."


class FakeRunner:
    def __init__(self, *, sufficient: bool = True, invalid: bool = False, visual: bool = False) -> None:
        self.calls: list = []
        self.sufficient, self.invalid, self.visual = sufficient, invalid, visual

    def run(self, *, request, evidence, feedback) -> AnswerDraft:
        self.calls.append((evidence, feedback))
        source = next((e for e in evidence if e.kind == ("vision" if self.visual else "text")), evidence[0])
        return AnswerDraft(sufficient=self.sufficient, search_terms=["replicates"], claims=[AnswerClaim(
            claim_id="c1", statement="该实验使用三个生物学重复。", basis="visual" if self.visual else "text",
            evidence_ids=["fabricated" if self.invalid else source.evidence_id], evidence=[source.excerpt])])


class FakeChecker:
    def run(self, *, document, analysis_result, **kwargs) -> FactCheckBatch:
        return FactCheckBatch(checks=[FactCheckItem(claim_id=c["claim_id"], claim=c["statement"],
            verdict="supported", evidence_ids=c["evidence_ids"], evidence_refs=c["evidence"])
            for c in analysis_result.structured_data["claims"]])


class FakeVision:
    def extract(self, *, document, figures) -> FigureSemanticArtifactBatch:
        return FigureSemanticArtifactBatch(artifacts=[FigureSemanticArtifact(
            figure_id=figures[0].figure_id, extraction_source="multimodal_llm", confidence="高",
            image_block_paths=["/test/page_1.png"], direct_evidence=["图中显示三个独立生物学重复的测量点。"],
            panels=[FigurePanel(panel_label="a", summary="子图中显示三个独立生物学重复测量点。", confidence="高")])])


def document() -> ParsedDocument:
    return ParsedDocument(title="Synthetic ATAC", metadata={"ordered_blocks": [
        {"block_id": f"p1_b{i}", "page_number": 1, "text": QUOTE, "bbox": [1, 2, 3, 4]} for i in range(15)]},
        figures=[FigureMetadata(figure_id="Figure 1", page_number=1, caption="Figure 1. " + QUOTE)])


class QuestionAnswerTests(unittest.TestCase):
    def pipeline(self, runner=None, vision=None) -> QuestionAnswerPipeline:
        return QuestionAnswerPipeline(runner=runner or FakeRunner(), checker=FakeChecker(),
                                     vision=vision or NoopFigureSemanticExtractor())

    def test_schema_limits(self):
        for payload in ({"question": " "}, {"question": "问题", "max_followups": 3},
                        {"question": "问题", "panel": "a"}, {"question": "问题", "figure": "../1"}):
            with self.assertRaises(ValidationError):
                QuestionRequest(**payload)

    def test_single_round_localized_answer(self):
        runner = FakeRunner()
        response = self.pipeline(runner).run(document=document(), request=QuestionRequest(question="ATAC 重复数？", max_followups=0))
        self.assertEqual(response.status, "answered")
        self.assertEqual(len(runner.calls), 1)
        self.assertEqual(response.evidence[0].page, 1)
        self.assertEqual(response.evidence[0].bbox, [1, 2, 3, 4])
        self.assertEqual(response.visual_status, "not_requested")

    def test_fabricated_evidence_refused_and_bounded(self):
        runner = FakeRunner(invalid=True)
        response = self.pipeline(runner).run(document=document(), request=QuestionRequest(question="重复？"))
        self.assertEqual(response.status, "refused")
        self.assertEqual(response.followups, 2)
        self.assertEqual(len(runner.calls), 3)
        self.assertEqual([len(call[0]) for call in runner.calls], [4, 8, 12])
        self.assertTrue(runner.calls[1][1])

    def test_visual_failure_cannot_release_visual_claim(self):
        response = self.pipeline(FakeRunner(visual=True)).run(document=document(),
            request=QuestionRequest(question="图中重复数？", figure="1", max_followups=0))
        self.assertEqual(response.visual_status, "failed")
        self.assertEqual(response.status, "refused")
        self.assertFalse(response.claims)

    def test_caption_only_can_be_partial(self):
        response = self.pipeline().run(document=document(), request=QuestionRequest(question="重复？", figure="1"))
        self.assertEqual(response.status, "partial")
        self.assertEqual(response.visual_status, "failed")

    def test_panel_success_and_missing_panel(self):
        for panel, status in (("a", "answered"), ("b", "refused")):
            response = self.pipeline(FakeRunner(visual=True), FakeVision()).run(document=document(),
                request=QuestionRequest(question="图中重复数？", figure="1", panel=panel, max_followups=0))
            self.assertEqual(response.status, status)
            if panel == "a":
                self.assertEqual(response.evidence[0].panel, "a")
                self.assertEqual(response.evidence[0].image_pages, [1])

    def test_unknown_figure_and_empty_document_refused(self):
        runner = FakeRunner()
        for source, request in ((document(), QuestionRequest(question="图9说明什么？")),
                                (ParsedDocument(), QuestionRequest(question="结论？"))):
            response = self.pipeline(runner).run(document=source, request=request)
            self.assertEqual(response.status, "refused")
        self.assertFalse(runner.calls)

    def test_model_failure_refused(self):
        class BrokenRunner:
            def run(self, **kwargs):
                raise RuntimeError("secret provider response")
        response = self.pipeline(BrokenRunner()).run(document=document(), request=QuestionRequest(question="重复？"))
        self.assertEqual(response.status, "refused")
        self.assertNotIn("secret", response.model_dump_json())

    def test_correction_recovers_after_qc_feedback(self):
        class CorrectingRunner(FakeRunner):
            def run(self, **kwargs):
                self.invalid = not self.calls
                return super().run(**kwargs)
        runner = CorrectingRunner()
        response = self.pipeline(runner).run(document=document(), request=QuestionRequest(question="重复？"))
        self.assertEqual(response.status, "answered")
        self.assertEqual(response.followups, 1)
        self.assertTrue(runner.calls[1][1])

    def test_ambiguous_figure_does_not_choose_arbitrarily(self):
        source = document()
        source.figures.append(source.figures[0].model_copy(update={"figure_id": "Figure 2"}))
        response = self.pipeline().run(document=source, request=QuestionRequest(question="这张图说明什么？"))
        self.assertEqual(response.status, "refused")

    def test_panel_is_inferred_even_with_explicit_figure(self):
        response = self.pipeline(FakeRunner(visual=True), FakeVision()).run(document=document(),
            request=QuestionRequest(question="图1a中显示什么？", figure="1", max_followups=0))
        self.assertEqual(response.request.panel, "a")
        self.assertEqual(response.status, "answered")

    def test_real_pdf_parser_service_and_persistence(self):
        import fitz
        with tempfile.TemporaryDirectory() as root:
            pdf = fitz.open()
            page = pdf.new_page()
            page.insert_text((50, 50), QUOTE)
            content = pdf.tobytes()
            pdf.close()
            service = QuestionAnswerService(parser=PdfParser(), pipeline=self.pipeline(), root=Path(root))
            response = asyncio.run(service.ask(filename="../paper.pdf", content=content,
                request=QuestionRequest(question="ATAC 重复？", max_followups=0)))
            self.assertEqual(response.status, "answered")
            self.assertEqual(service.get(response.id), response)
            self.assertTrue((Path(root) / str(response.id) / "parsed.json").exists())
            with self.assertRaises(ValueError):
                asyncio.run(service.ask(filename="paper.pdf", content=b"broken", request=response.request))
