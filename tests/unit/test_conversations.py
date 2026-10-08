import asyncio
import tempfile
import unittest
from pathlib import Path

import fitz

from paper_analysis.adapters.parser.pdf import PdfParser
from paper_analysis.adapters.parser.mcp_figure_semantics import NoopFigureSemanticExtractor
from paper_analysis.domain.qa import QuestionRequest
from paper_analysis.services.conversations import ConversationService
from paper_analysis.services.question_answer_service import QuestionAnswerService
from paper_analysis.runtime.pipelines.question_answer import QuestionAnswerPipeline
from test_question_answer import FakeRunner, FakeChecker, QUOTE


class ConversationTests(unittest.TestCase):
    def test_turn_reuses_document_and_budget_and_blocks_overlap(self):
        with tempfile.TemporaryDirectory() as root:
            service = QuestionAnswerService(parser=PdfParser(render_assets=False), root=Path(root),
                pipeline=QuestionAnswerPipeline(runner=FakeRunner(), checker=FakeChecker(), vision=NoopFigureSemanticExtractor()))
            pdf = fitz.open(); pdf.new_page().insert_text((50, 50), QUOTE)
            content = pdf.tobytes(); pdf.close()
            answer = asyncio.run(service.ask(filename="synthetic.pdf", content=content, request=QuestionRequest(question="重复数？", max_followups=0)))
            conversations = ConversationService(service)
            conversation = conversations.create(answer.id)
            self.assertEqual(conversations.create(answer.id).id, conversation.id)
            with self.assertRaisesRegex(ValueError, "指代"):
                conversations.prepare_turn(conversation.id, QuestionRequest(question="它是什么意思？"))
            turn = conversations.prepare_turn(conversation.id, QuestionRequest(question="解释生物学重复", max_followups=0))
            with self.assertRaisesRegex(ValueError, "上一轮"):
                conversations.prepare_turn(conversation.id, QuestionRequest(question="再问"))
            turn.status = "running"; service.store.save(turn)
            result = service.execute(turn.id, turn.attempt)
            service.complete(turn, result)
            self.assertEqual(result.document_sha256, answer.document_sha256)
            self.assertGreater(result.execution.call_count, answer.execution.call_count)
            self.assertEqual(service.audit(turn.id).parse_cache_hit, True)
            self.assertEqual(service.audit(answer.id).execution.call_count, answer.execution.call_count)
