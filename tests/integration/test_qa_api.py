import asyncio
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from paper_analysis.api.app import create_app
from paper_analysis.api.routes.questions import get_question_service
from paper_analysis.domain.qa import AnswerResponse
from paper_analysis.domain.quality import QualityReport
from paper_analysis.domain.schemas import ParsedDocument
from paper_analysis.services.question_answer_service import QuestionAnswerService
from paper_analysis.services.question_jobs import QuestionJobs


class FakeParser:
    async def parse(self, path: Path) -> ParsedDocument:
        return ParsedDocument(title="离线测试")


class FakePipeline:
    def run(self, *, document, request) -> AnswerResponse:
        return AnswerResponse(request=request, status="refused", answer="证据不足，暂不能回答。",
                              quality=QualityReport(status="blocked"))


class QuestionApiTests(unittest.TestCase):
    def test_upload_answer_reload_and_validation(self):
        with tempfile.TemporaryDirectory() as root:
            service = QuestionAnswerService(parser=FakeParser(), pipeline=FakePipeline(), root=Path(root))
            async def worker(job):
                return await asyncio.to_thread(service.execute, job.id, job.attempt)
            app = create_app(qa_jobs=QuestionJobs(service, worker=worker))
            app.dependency_overrides[get_question_service] = lambda: service
            with TestClient(app) as client:
                response = client.post("/api/qa/questions", files={"file": ("paper.pdf", b"%PDF-fake")},
                                       data={"question": "图1是否支持因果关系？", "max_followups": 0})
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["status"], "refused")
                self.assertEqual(client.get(f'/api/qa/questions/{payload["id"]}').json(), payload)
                for data in ({"question": " "}, {"question": "问题", "panel": "a"},
                             {"question": "问题", "max_followups": 3}):
                    self.assertEqual(client.post("/api/qa/questions", files={"file": ("p.pdf", b"%PDF-")}, data=data).status_code, 422)
                self.assertEqual(client.post("/api/qa/questions", files={"file": ("p.pdf", b"broken")},
                                             data={"question": "问题"}).status_code, 400)
                self.assertEqual(client.get("/api/qa/questions/00000000-0000-0000-0000-000000000000").status_code, 404)
                self.assertIn("/api/analysis/jobs", app.openapi()["paths"])
