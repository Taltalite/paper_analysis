import json
import tempfile
import unittest
from pathlib import Path

from paper_analysis.adapters.llm.visual_check import ImageClaimChecker
from paper_analysis.adapters.parser.multimodal_figure_semantics import MultimodalFigureSemanticExtractor
from paper_analysis.domain.qa import AnswerClaim, QuestionRequest, VisualClaimCheck, VisualCheckBatch
from paper_analysis.runtime.pipelines.question_answer import QuestionAnswerPipeline
from paper_analysis.runtime.pipelines.visual_review import VisualReviewSession
from test_question_answer import FakeChecker, FakeRunner, FakeVision, document


class RecordingChecker:
    def __init__(self, verdicts=None):
        self.verdicts = verdicts or ["supported"]
        self.calls = []

    def check(self, *, request, claims, image_paths):
        self.calls.append((request, claims, image_paths))
        verdict = self.verdicts[min(len(self.calls)-1, len(self.verdicts)-1)]
        return VisualCheckBatch(checks=[VisualClaimCheck(claim_id=c.claim_id, statement=c.statement,
            verdict=verdict, observation="实际图像标签需要逐个核对。", rationale="以实际页面为依据。") for c in claims])


class VisualReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.image = Path(self.temp.name) / "page_1.png"
        self.image.write_bytes(b"synthetic-image")
        self.request = QuestionRequest(question="图1a标签", figure="1", panel="a")
        self.claim = AnswerClaim(claim_id="c1", statement="标签是红色 m6G37。", basis="visual")

    def test_cache_and_budget_bind_exact_claim_and_image(self):
        checker = RecordingChecker()
        session = VisualReviewSession(checker)
        args = dict(request=self.request, claims=[self.claim], image_paths=[self.image])
        self.assertEqual(session.review(**args).status, "reviewed")
        self.assertTrue(session.review(**args).reused)
        self.image.write_bytes(b"changed-image")
        self.assertFalse(session.review(**args).reused)
        self.claim.statement = "更换后的主张。"
        self.assertEqual(session.review(**args).status, "budget_exhausted")
        self.assertEqual(len(checker.calls), 2)
        self.assertEqual(VisualReviewSession(checker).review(**args).calls_used, 1)

    def test_missing_duplicate_mismatch_and_error_fail_closed(self):
        for kind in ("missing", "duplicate", "mismatch", "exception"):
            class Broken(RecordingChecker):
                def check(inner, **kwargs):
                    batch = super().check(**kwargs)
                    if kind == "missing": batch.checks = []
                    if kind == "duplicate": batch.checks *= 2
                    if kind == "mismatch": batch.checks[0].statement = "另一个主张"
                    if kind == "exception": raise RuntimeError("secret-response")
                    return batch
            result = VisualReviewSession(Broken()).review(request=self.request, claims=[self.claim], image_paths=[self.image])
            self.assertEqual(result.status, "failed")
            self.assertNotIn("secret", result.model_dump_json())

    def test_conflict_feedback_then_corrected_claim_is_reviewed_again(self):
        class Correcting(FakeRunner):
            def run(inner, **kwargs):
                draft = super().run(**kwargs)
                draft.claims[0].statement = "初次错误的视觉主张。" if len(inner.calls) == 1 else "修正后的视觉主张。"
                return draft
        runner, checker, audit = Correcting(visual=True), RecordingChecker(["conflicting", "supported"]), []
        source = document()
        source.figures[0].page_snapshot_path = str(self.image)
        pipeline = QuestionAnswerPipeline(runner=runner, checker=FakeChecker(), vision=FakeVision(), visual_checker=checker)
        answer = pipeline.run(document=source, request=self.request, audit_sink=audit.append)
        self.assertEqual(answer.status, "answered")
        self.assertEqual(len(audit), 2)
        self.assertEqual(audit[0].visual_review.checks[0].verdict, "conflicting")
        self.assertEqual(answer.visual_checks[0].verdict, "supported")
        self.assertIn("实际图像", " ".join(runner.calls[1][1]))
        self.assertEqual(checker.calls[0][2], [self.image])

    def test_missing_real_page_never_releases_visual_claim(self):
        checker = RecordingChecker()
        answer = QuestionAnswerPipeline(runner=FakeRunner(visual=True), checker=FakeChecker(),
            vision=FakeVision(), visual_checker=checker).run(document=document(), request=self.request)
        self.assertEqual(answer.status, "refused")
        self.assertFalse(checker.calls)
        self.assertFalse(answer.visual_checks)

    def test_adapter_sends_image_without_prior_ocr(self):
        claim = self.claim
        class Client:
            def complete_with_images(inner, **kwargs):
                self.assertEqual(kwargs["image_paths"], [self.image])
                self.assertNotIn("OLD_OCR_SECRET", kwargs["prompt"])
                return json.dumps({"checks": [dict(claim_id=claim.claim_id, statement=claim.statement,
                    verdict="conflicting", observation="黑色 m1G37", rationale="上标与颜色不符")]})
        self.claim.evidence = ["OLD_OCR_SECRET"]
        result = ImageClaimChecker(Client()).check(request=self.request, claims=[self.claim], image_paths=[self.image])
        self.assertEqual(result.checks[0].verdict, "conflicting")

    def test_target_panel_uses_distinct_cache_and_prompt(self):
        class Client:
            vision_model = "fake"
        extractor = MultimodalFigureSemanticExtractor(vision_client=Client())
        figure = document().figures[0]
        args = dict(figure=figure, image_paths=[self.image])
        self.assertNotEqual(extractor._cache_key(**args), extractor._cache_key(**args, panel="a"))
        self.assertNotEqual(extractor._cache_key(**args, panel="a"), extractor._cache_key(**args, panel="b"))
        self.assertIn("只提取子图 a", extractor._build_prompt(figure, "a"))
