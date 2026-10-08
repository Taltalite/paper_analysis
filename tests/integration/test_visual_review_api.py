import asyncio
import tempfile
import unittest
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from paper_analysis.adapters.parser.pdf import PdfParser
from paper_analysis.adapters.parser.qa_cache import OnDemandFigureExtractor
from paper_analysis.api.app import create_app
from paper_analysis.api.routes.questions import get_question_service
from paper_analysis.domain.models import FactCheckBatch, FactCheckItem, FigurePanel, FigureSemanticArtifact, FigureSemanticArtifactBatch
from paper_analysis.domain.qa import AnswerClaim, AnswerDraft, VisualClaimCheck, VisualCheckBatch
from paper_analysis.runtime.pipelines.question_answer import QuestionAnswerPipeline
from paper_analysis.services.question_answer_service import QuestionAnswerService
from paper_analysis.services.question_jobs import QuestionJobs


class VisualReviewApiTests(unittest.TestCase):
    def test_real_parser_to_visual_correction_audit_and_page(self):
        class Extractor:
            def extract(self, *, document, figures):
                f = figures[0]
                return FigureSemanticArtifactBatch(artifacts=[FigureSemanticArtifact(
                    figure_id=f.figure_id, extraction_source="multimodal_llm", confidence="高",
                    image_block_paths=[f.page_snapshot_path],
                    panels=[FigurePanel(panel_label="a", confidence="高", summary="此子图显示测试用标签及一条横向曲线。")])])
        class Runner:
            calls = 0
            def run(self, *, request, evidence, feedback):
                self.calls += 1
                e = next(e for e in evidence if e.kind == "vision")
                return AnswerDraft(sufficient=True, claims=[AnswerClaim(claim_id="v1", basis="visual",
                    statement="错误颜色。" if self.calls == 1 else "已修正颜色。", evidence=[e.excerpt], evidence_ids=[e.evidence_id])])
        class Checker:
            def run(self, *, analysis_result, **kwargs):
                return FactCheckBatch(checks=[FactCheckItem(claim_id=c['claim_id'], claim=c['statement'], verdict="supported",
                    evidence_refs=c['evidence'], evidence_ids=c['evidence_ids']) for c in analysis_result.structured_data['claims']])
        class Reviewer:
            def check(self, *, claims, image_paths, **kwargs):
                assert image_paths[0].read_bytes().startswith(b'\x89PNG')
                return VisualCheckBatch(checks=[VisualClaimCheck(claim_id=c.claim_id, statement=c.statement,
                    verdict="conflicting" if c.statement == "错误颜色。" else "supported",
                    observation="图像中的测试标记。", rationale="重新观察实际图片。") for c in claims])
        with fitz.open() as pdf:
            page = pdf.new_page()
            page.draw_rect(fitz.Rect(40, 40, 160, 120))
            page.insert_text((40, 180), "Figure 1. A synthetic diagram used only for offline testing.")
            content = pdf.tobytes()
        with tempfile.TemporaryDirectory() as root:
            service = QuestionAnswerService(parser=PdfParser(render_assets=False), root=Path(root), pipeline=
                QuestionAnswerPipeline(runner=Runner(), checker=Checker(), vision=OnDemandFigureExtractor(Extractor()), visual_checker=Reviewer()))
            async def worker(job):
                return await asyncio.to_thread(service.execute, job.id, job.attempt)
            app = create_app(qa_jobs=QuestionJobs(service, worker=worker))
            app.dependency_overrides[get_question_service] = lambda: service
            with TestClient(app) as client:
                response = client.post('/api/qa/questions', files={'file': ('synthetic.pdf', content)},
                    data={'question': '图1a标签？', 'figure': '1', 'panel': 'a', 'max_followups': '1'})
                self.assertEqual(response.status_code, 200)
                answer = response.json()
                self.assertEqual(answer['answer'], '已修正颜色。')
                self.assertEqual(answer['visual_checks'][0]['verdict'], 'supported')
                audit = client.get(f"/api/qa/questions/{answer['id']}/audit").json()
                self.assertEqual([r['visual_review']['checks'][0]['verdict'] for r in audit['rounds']], ['conflicting', 'supported'])
                self.assertTrue(audit['rounds'][0]['visual_review']['image_sha256'])
                self.assertEqual(audit['rounds'][1]['visual_review']['calls_used'], 2)
                page = client.get(f"/api/qa/questions/{answer['id']}/pages/1", params={'evidence_id': answer['evidence'][0]['evidence_id']})
                self.assertEqual(page.status_code, 200)
                self.assertTrue(page.content.startswith(b'\x89PNG'))
                created = client.post(f"/api/qa/questions/{answer['id']}/conversation")
                self.assertEqual(created.status_code, 200)
                conversation = created.json()
                self.assertEqual(conversation['document_sha256'], answer['document_sha256'])
                restored = client.get(f"/api/qa/conversations/{conversation['id']}")
                self.assertEqual(restored.json()['turns'], [answer['id']])
                turn = client.post(f"/api/qa/conversations/{conversation['id']}/turns",
                    json={'question': '这张图的标签是什么？', 'max_followups': 0})
                self.assertEqual(turn.status_code, 202)
                self.assertEqual(turn.json()['parent_turn_id'], answer['id'])
                self.assertEqual(turn.json()['request']['figure'], '1')
