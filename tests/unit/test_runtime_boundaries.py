import asyncio
import threading
import unittest
from concurrent.futures import Future
from unittest.mock import Mock
from uuid import uuid4

from pydantic import ValidationError

from paper_analysis.domain.schemas import ParsedDocument
from paper_analysis.runtime.pipelines.research_paper import ResearchPaperPipeline
from paper_analysis.services.job_executor import InProcessJobExecutor
from paper_analysis.tools.document_tools import DocumentKeywordSearch, DocumentSectionExtractor, KeywordQuery


class RuntimeBoundaryTests(unittest.TestCase):
    def test_focus_budget_preserves_methods_results_after_long_intro(self) -> None:
        sections = {"abstract": "A" * 50000, "introduction": "I" * 50000,
                    "method": "METHOD " * 5000, "results": "RESULT " * 5000}
        source = ParsedDocument(raw_text="raw", sections=sections, section_order=list(sections))
        focused, included = ResearchPaperPipeline._build_focus_document(source)
        self.assertLessEqual(len(focused.raw_text), 12000)
        self.assertIn("METHOD", focused.raw_text)
        self.assertIn("RESULT", focused.raw_text)
        self.assertEqual(included, list(sections))
        self.assertEqual(source.sections["abstract"], "A" * 50000)

    def test_bound_tools_reject_replacement_text_and_keep_evidence_scope(self) -> None:
        source = ParsedDocument(raw_text="limited", sections={"results": "Bound evidence only."},
            metadata={"ordered_blocks": [{"block_id": "p2_b1", "page_number": 2, "text": "Bound evidence only."}]})
        search, section = DocumentKeywordSearch(source), DocumentSectionExtractor(source)
        with self.assertRaises(ValidationError):
            KeywordQuery.model_validate({"keyword": "fake", "paper_text": "fabricated evidence"})
        source.metadata["ordered_blocks"][0]["text"] = "mutated"
        self.assertIn("p2_b1", search._run(keyword="Bound"))
        self.assertNotIn("mutated", search._run(keyword="mutated"))
        self.assertIn("Bound evidence only.", section._run(section_name="results"))
        self.assertIn("未找到", section._run(section_name="methods"))
        self.assertNotIn("paper_text", search.args_schema.model_json_schema()["properties"])
        with self.assertRaises(ValidationError):
            search._run(keyword="Bound", max_hits=10000)

    def test_already_completed_report_future_does_not_deadlock(self) -> None:
        executor = InProcessJobExecutor.__new__(InProcessJobExecutor)
        executor._lock = threading.Lock()
        executor._futures = {}
        completed = Future()
        completed.set_result(None)
        executor._executor = Mock()
        executor._executor.submit.return_value = completed
        errors = []
        def run() -> None:
            try:
                asyncio.run(executor.submit_job(job_service=Mock(), job_id=uuid4()))
            except Exception as exc:
                errors.append(exc)
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive(), "同步完成的 Future 回调导致死锁")
        self.assertFalse(errors)
        self.assertFalse(executor._futures)
