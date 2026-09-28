import asyncio
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from paper_analysis.services.qa_evaluation import run_candidates


class EvaluationSeparationTests(unittest.TestCase):
    def test_configuration_failure_is_saved_without_expert_score(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            source = directory / "source.pdf"
            source.write_bytes(b"%PDF-test")
            manifest = directory / "cases.jsonl"
            manifest.write_text(json.dumps({"id": "configured", "question": "问题",
                "paper": {"source_path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}}))
            with patch("paper_analysis.services.qa_evaluation.build_question_answer_service", side_effect=ValueError("secret")):
                results = asyncio.run(run_candidates(manifest, directory / "run", real=True))
            self.assertEqual(results[0].execution, "configuration_failed")
            payload = (directory / "run/manifest.json").read_text()
            self.assertNotIn("secret", payload)
            self.assertIn("not_evaluated", payload)
            self.assertEqual(len(list((directory / "run").glob("manifest-*.json"))), 1)

    def test_unbound_and_fingerprint_mismatch_never_call_model(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            source = directory / "source.pdf"
            source.write_bytes(b"%PDF-test")
            cases = [{"id": "unbound", "question": "问题"}, {"id": "wrong-hash", "question": "问题",
                     "paper": {"source_path": str(source), "sha256": "wrong"}}]
            manifest = directory / "cases.jsonl"
            manifest.write_text("\n".join(json.dumps(case) for case in cases))
            with patch("paper_analysis.services.qa_evaluation.build_question_answer_service") as factory:
                results = asyncio.run(run_candidates(manifest, directory / "run", real=True))
            factory.assert_not_called()
            self.assertTrue(all(r.execution == "not_called" for r in results))
            self.assertTrue(all(r.expert_evaluation == "not_evaluated" for r in results))
