from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from paper_analysis.domain.execution import ResolvedPolicy
from paper_analysis.services.paper_baseline import run_paper_batches
from paper_analysis.services.qa_evaluation import CandidatePaper, EvaluationManifest, QuestionCandidate


class PaperBaselineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest = self.root / "candidates.jsonl"
        self.output = self.root / "run"
        self.candidates: list[QuestionCandidate] = []
        for paper, count in (("A", 3), ("B", 2)):
            source = self.root / f"{paper}.pdf"
            source.write_bytes(f"source {paper}".encode())
            for index in range(count):
                self.candidates.append(QuestionCandidate(id=f"{paper}-{index}", question="测试问题",
                    paper=CandidatePaper(source_path=str(source), sha256=hashlib.sha256(source.read_bytes()).hexdigest())))
        self.manifest.write_text("\n".join(c.model_dump_json() for c in self.candidates) + "\n")

    async def test_separate_paper_runs_use_default_budget_without_model_calls(self) -> None:
        report = await run_paper_batches(self.manifest, self.output)
        policy = ResolvedPolicy.resolve().effective
        self.assertEqual(len(report.results), 5)
        self.assertEqual(report.run_settings["paper_batches"], 2)
        self.assertEqual(report.run_settings["token_budget_per_paper"], 300_000)
        self.assertEqual(report.run_settings["max_output_tokens"], 65_536)
        batches = [EvaluationManifest.model_validate_json(p.read_text()) for p in self.output.glob("manifest-*.json")]
        self.assertEqual(len({b.run_id for b in batches}), 2)
        self.assertEqual({frozenset(r.candidate_id for r in b.results) for b in batches},
                         {frozenset(("A-0", "A-1", "A-2")), frozenset(("B-0", "B-1"))})
        for batch in batches:
            self.assertEqual(batch.run_settings["token_budget"], policy.token_budget)
            self.assertEqual(batch.run_settings["max_calls"], policy.max_calls)
            self.assertTrue(all(r.execution == "not_called" for r in batch.results))
        self.assertTrue((self.output / "baseline_manifest.json").is_file())

    async def test_duplicate_ids_rejected_before_execution(self) -> None:
        self.candidates.append(self.candidates[0])
        self.manifest.write_text("\n".join(c.model_dump_json() for c in self.candidates) + "\n")
        with self.assertRaisesRegex(ValueError, "重复 ID"):
            await run_paper_batches(self.manifest, self.output)
        self.assertFalse(self.output.exists())

    async def test_partial_run_is_preserved(self) -> None:
        self.output.mkdir()
        history = self.output / "manifest.json"
        history.write_text("existing run")
        with self.assertRaisesRegex(ValueError, "保留历史"):
            await run_paper_batches(self.manifest, self.output)
        self.assertEqual(history.read_text(), "existing run")


if __name__ == "__main__":
    unittest.main()
