from __future__ import annotations

import asyncio
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import sys

from paper_analysis.adapters.parser.pdf import PdfParser
from paper_analysis.adapters.parser.qa_cache import ParsedDocumentCache, OnDemandFigureExtractor
from paper_analysis.adapters.parser.mcp_figure_semantics import NoopFigureSemanticExtractor
from paper_analysis.domain.qa import QuestionRequest, AnswerDraft, AnswerClaim, AnswerResponse
from paper_analysis.domain.quality import QualityReport
from paper_analysis.services.question_answer_service import QuestionAnswerService
from paper_analysis.services.question_jobs import QuestionJobs
from test_question_answer import FakeRunner, FakeChecker, FakeVision, document, QuestionAnswerPipeline


def pdf_bytes(text: str = "Figure 1. Three biological replicates were used for ATAC-seq.") -> bytes:
    import fitz
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((50, 250), text)
        page.draw_rect(fitz.Rect(50, 50, 150, 150))
        return pdf.tobytes()


def pipeline(runner=None, vision=None, checker=None):
    return QuestionAnswerPipeline(runner=runner or FakeRunner(), checker=checker or FakeChecker(),
                                 vision=vision or NoopFigureSemanticExtractor())


class EvidenceEngineeringTests(unittest.TestCase):
    def test_checker_quote_cannot_rescue_forged_claim_quote(self):
        class Forged(FakeRunner):
            def run(self, **kwargs):
                draft = super().run(**kwargs)
                draft.claims[0].evidence = ["This quotation is entirely fabricated."]
                return draft
        class Rescue(FakeChecker):
            def run(self, **kwargs):
                batch = super().run(**kwargs)
                batch.checks[0].evidence_refs = ["Three biological replicates were used for ATAC-seq."]
                return batch
        answer = pipeline(Forged(), checker=Rescue()).run(document=document(), request=QuestionRequest(question="重复？", max_followups=0))
        self.assertEqual(answer.status, "refused")
        self.assertTrue(any(i.code == "qa_evidence_mismatch" for i in answer.quality.issues))

    def test_wrong_page_visual_artifact_is_not_released(self):
        class WrongPage(FakeVision):
            def extract(self, **kwargs):
                batch = super().extract(**kwargs)
                batch.artifacts[0].image_block_paths = ["/test/page_99.png"]
                return batch
        answer = pipeline(FakeRunner(visual=True), WrongPage()).run(document=document(),
            request=QuestionRequest(question="图1a", figure="1", panel="a", max_followups=0))
        self.assertEqual(answer.status, "refused")
        self.assertEqual(answer.visual_status, "failed")

    def test_later_failure_keeps_verified_partial_and_audit(self):
        class FailsLater(FakeRunner):
            def run(self, **kwargs):
                if self.calls:
                    raise RuntimeError("fake timeout")
                return super().run(**kwargs)
        audit = []
        answer = pipeline(FailsLater(sufficient=False)).run(document=document(),
            request=QuestionRequest(question="ATAC 重复？"), audit_sink=audit.append)
        self.assertEqual(answer.status, "partial")
        self.assertEqual(len(answer.claims), 1)
        self.assertEqual(answer.stop_reason, "model_error")
        self.assertEqual(len(audit), 2)
        self.assertIsNotNone(audit[0].checks)
        self.assertIsNotNone(audit[1].error)

    def test_no_new_evidence_stops_early(self):
        source = document()
        source.metadata["ordered_blocks"] = source.metadata["ordered_blocks"][:1]
        runner = FakeRunner(sufficient=False)
        answer = pipeline(runner).run(document=source, request=QuestionRequest(question="重复？"))
        self.assertEqual(len(runner.calls), 1)
        self.assertEqual(answer.stop_reason, "no_new_evidence")

    def test_new_conflict_does_not_resurrect_previous_claim(self):
        class ConflictsLater(FakeChecker):
            calls = 0
            def run(self, **kwargs):
                result = super().run(**kwargs)
                self.calls += 1
                if self.calls > 1:
                    result.checks[0].verdict = "conflicting"
                return result
        answer = pipeline(FakeRunner(sufficient=False), checker=ConflictsLater()).run(
            document=document(), request=QuestionRequest(question="ATAC 重复？"))
        self.assertEqual(answer.status, "refused")
        self.assertFalse(answer.claims)

    def test_gap_targets_statistics_block(self):
        class Gaps(FakeRunner):
            def run(self, **kwargs):
                result = super().run(**kwargs)
                result.evidence_gaps = ["statistics"]
                return result
        source = document()
        source.metadata["ordered_blocks"].append({"block_id": "stats", "page_number": 2,
            "text": "Statistical test was applied with standard deviation and p-value correction."})
        runner = Gaps(sufficient=False)
        pipeline(runner).run(document=source, request=QuestionRequest(question="ATAC？"))
        self.assertIn("stats", [e.evidence_id for e in runner.calls[1][0]])


class CacheEngineeringTests(unittest.TestCase):
    def test_scanned_page_and_damaged_pdf_do_not_invent_evidence(self):
        import fitz
        with tempfile.TemporaryDirectory() as root:
            with fitz.open() as pdf:
                page = pdf.new_page()
                page.draw_rect(fitz.Rect(10, 10, 100, 100))
                content = pdf.tobytes()
            runner = FakeRunner()
            service = QuestionAnswerService(parser=PdfParser(render_assets=False), pipeline=pipeline(runner), root=Path(root))
            response = asyncio.run(service.ask(filename="scan.pdf", content=content,
                request=QuestionRequest(question="实验结论？")))
            self.assertEqual(response.status, "refused")
            self.assertFalse(runner.calls)
            with self.assertRaises(ValueError):
                asyncio.run(service.ask(filename="broken.pdf", content=b"%PDF-damaged",
                    request=QuestionRequest(question="实验结论？")))
            self.assertTrue(any(job.status == "failed" for job in service.store.list()))

    def test_concurrent_cache_hit_invalidation_and_lazy_render(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "input.pdf"
            source.write_bytes(pdf_bytes())
            cache = ParsedDocumentCache(Path(root) / "cache", PdfParser(render_assets=False))
            with ThreadPoolExecutor(max_workers=2) as pool:
                values = list(pool.map(lambda _: cache.get(source), range(2)))
            self.assertEqual(sorted(hit for _, hit in values), [False, True])
            parsed = values[0][0]
            self.assertFalse(Path(parsed.figures[0].page_snapshot_path).exists())
            OnDemandFigureExtractor(NoopFigureSemanticExtractor()).extract(document=parsed, figures=parsed.figures[:1])
            self.assertTrue(Path(parsed.figures[0].page_snapshot_path).exists())
            fingerprint = parsed.metadata["document_sha256"]
            source.write_bytes(pdf_bytes("Figure 1. Different experiment and different source bytes."))
            changed, hit = cache.get(source)
            self.assertFalse(hit)
            self.assertNotEqual(fingerprint, changed.metadata["document_sha256"])
            cache.version += "-new"
            self.assertFalse(cache.get(source)[1])
            artifact = Path(cache.get(source)[0].metadata["source_path"]).parent / "parsed.json"
            artifact.write_text('{}')
            self.assertFalse(cache.get(source)[1])


class JobEngineeringTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = QuestionAnswerService(parser=PdfParser(render_assets=False), pipeline=pipeline(), root=Path(self.temp.name))

    async def asyncTearDown(self):
        self.temp.cleanup()

    def submit(self, manager):
        return manager.submit(filename="p.pdf", content=pdf_bytes("Three biological replicates were used for ATAC-seq."),
                              request=QuestionRequest(question="ATAC 重复？", max_followups=0))

    async def test_completion_audit_binding_retry_and_recovery(self):
        async def worker(job):
            return await asyncio.to_thread(self.service.execute, job.id, job.attempt)
        manager = QuestionJobs(self.service, worker=worker)
        await manager.start()
        job = self.submit(manager)
        await manager.tasks[job.id]
        self.assertEqual(self.service.store.get(job.id).status, "completed")
        audit = self.service.audit(job.id)
        self.assertEqual(audit.document_sha256, self.service.get(job.id).document_sha256)
        self.assertEqual(audit.execution_kind, "offline_test")
        self.assertEqual(len(audit.rounds), 1)
        with self.assertRaises(ValueError):
            manager.retry(job.id)
        pending = self.service.prepare(filename="p.pdf", content=pdf_bytes(), request=job.request)
        pending.status = "running"
        self.service.store.save(pending)
        await manager.close()
        replacement = QuestionJobs(self.service, worker=worker)
        await replacement.start()
        self.assertEqual(self.service.store.get(pending.id).status, "failed")
        retry = replacement.retry(pending.id)
        await replacement.tasks[retry.id]
        self.assertEqual(retry.attempt, 2)
        self.assertEqual(self.service.store.get(retry.id).status, "completed")
        await replacement.close()

    async def test_timeout_reaps_real_process_and_rejects_late_publish(self):
        real_spawn = asyncio.create_subprocess_exec
        processes = []
        async def sleeper(*args, **kwargs):
            process = await real_spawn(sys.executable, "-c", "import time; time.sleep(30)", **kwargs)
            processes.append(process)
            return process
        manager = QuestionJobs(self.service, timeout=0.1)
        await manager.start()
        with patch("paper_analysis.services.question_jobs.asyncio.create_subprocess_exec", sleeper):
            job = self.submit(manager)
            await manager.tasks[job.id]
        self.assertEqual(self.service.store.get(job.id).status, "timed_out")
        self.assertTrue(processes and processes[0].returncode is not None)
        with self.assertRaises(ValueError):
            await asyncio.to_thread(self.service.execute, job.id, job.attempt)
        late = AnswerResponse(id=job.id, request=job.request, status="refused", answer="迟到结果",
                              document_sha256=job.document_sha256, quality=QualityReport(status="blocked"))
        self.service.complete(job, late)
        with self.assertRaises(FileNotFoundError):
            self.service.get(job.id)
        await manager.close()

    async def test_cancel_and_single_supervisor(self):
        async def wait(job):
            await asyncio.sleep(30)
        manager = QuestionJobs(self.service, worker=wait)
        await manager.start()
        other = QuestionJobs(self.service)
        with self.assertRaises(RuntimeError):
            await other.start()
        job = self.submit(manager)
        await manager.cancel(job.id)
        self.assertEqual(self.service.store.get(job.id).status, "cancelled")
        await manager.close()
