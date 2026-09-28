import asyncio
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from paper_analysis.api.app import create_app
from paper_analysis.api.routes.questions import get_question_service
from paper_analysis.adapters.parser.pdf import PdfParser
from paper_analysis.domain.qa import AnswerResponse, AnswerClaim, EvidenceLocation
from paper_analysis.domain.quality import QualityReport
from paper_analysis.services.question_answer_service import QuestionAnswerService
from paper_analysis.services.question_jobs import QuestionJobs


class LocalPipeline:
    def run(self, *, document, request):
        block = next(b for b in document.metadata["ordered_blocks"] if b.get("text"))
        claim = AnswerClaim(claim_id="c1", statement="合成样本包含三个重复。", basis="text",
                            evidence_ids=[block["block_id"]], evidence=[block["text"]])
        return AnswerResponse(request=request, status="answered", answer=claim.statement, claims=[claim],
            evidence=[EvidenceLocation(evidence_id=block["block_id"], kind="text", page=block["page_number"],
                block_id=block["block_id"], bbox=block["bbox"], excerpt=block["text"])],
            quality=QualityReport(status="passed", accepted_claim_ids=["c1"]))


class BackgroundQuestionApiTests(unittest.TestCase):
    def test_job_result_audit_page_and_recovery_links(self):
        import fitz
        with fitz.open() as pdf:
            pdf.new_page().insert_text((40, 80), "Three biological replicates were used.")
            content = pdf.tobytes()
        with tempfile.TemporaryDirectory() as root:
            service = QuestionAnswerService(parser=PdfParser(render_assets=False), pipeline=LocalPipeline(), root=Path(root))
            async def worker(job):
                return await asyncio.to_thread(service.execute, job.id, job.attempt)
            manager = QuestionJobs(service, worker=worker)
            app = create_app(qa_jobs=manager)
            app.dependency_overrides[get_question_service] = lambda: service
            with TestClient(app) as client:
                response = client.post("/api/qa/jobs", files={"file": ("p.pdf", content)}, data={"question": "重复数？"})
                self.assertEqual(response.status_code, 202)
                identifier = response.json()["id"]
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    job = client.get(f"/api/qa/jobs/{identifier}").json()
                    if job["status"] not in {"queued", "running"}:
                        break
                    time.sleep(0.01)
                self.assertEqual(job["status"], "completed")
                self.assertEqual(client.get("/api/qa/jobs").json()[0]["id"], identifier)
                answer = client.get(f"/api/qa/questions/{identifier}").json()
                self.assertEqual(answer["document_sha256"], job["document_sha256"])
                audit = client.get(f"/api/qa/questions/{identifier}/audit").json()
                self.assertEqual(audit["document_sha256"], job["document_sha256"])
                evidence = answer["evidence"][0]
                endpoint = f"/api/qa/questions/{identifier}/pages/1"
                plain = client.get(endpoint)
                highlighted = client.get(endpoint, params={"evidence_id": evidence["evidence_id"]})
                self.assertEqual(highlighted.headers["content-type"], "image/png")
                self.assertNotEqual(plain.content, highlighted.content)
                self.assertEqual(client.get(endpoint, params={"evidence_id": "invented"}).status_code, 400)
                self.assertEqual(client.get(f"/api/qa/questions/{identifier}/pages/99").status_code, 400)
                self.assertEqual(client.post(f"/api/qa/jobs/{identifier}/retry").status_code, 409)
                self.assertEqual(client.get("/api/qa/jobs/not-a-uuid").status_code, 422)

    def test_sync_endpoint_timeout_is_not_a_completed_answer(self):
        with tempfile.TemporaryDirectory() as root:
            service = QuestionAnswerService(parser=PdfParser(), pipeline=LocalPipeline(), root=Path(root))
            async def sleeper(job):
                await asyncio.sleep(30)
            app = create_app(qa_jobs=QuestionJobs(service, timeout=0.02, worker=sleeper))
            app.dependency_overrides[get_question_service] = lambda: service
            with TestClient(app) as client:
                response = client.post("/api/qa/questions", files={"file": ("p.pdf", b"%PDF-")}, data={"question": "问题"})
                self.assertEqual(response.status_code, 504)
                self.assertEqual(client.get("/api/qa/jobs").json()[0]["status"], "timed_out")
