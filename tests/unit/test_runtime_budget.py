import asyncio
import unittest

from paper_analysis.domain.enums import AnalysisMode
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.crewai_runtime import CrewAIRuntime
from paper_analysis.runtime.pipelines.general_text import GeneralTextPipeline
from paper_analysis.domain.execution import ExecutionPolicyRequest


class _Runner:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, *, document, profile):
        self.calls += 1
        return AnalysisResult(title=document.title, summary="离线结果")


class RuntimeBudgetTests(unittest.TestCase):
    def test_report_runtime_persists_unknown_crewai_usage(self) -> None:
        runner = _Runner()
        runtime = CrewAIRuntime(
            general_text_pipeline=GeneralTextPipeline(crew_runner=runner),
            research_paper_pipeline=None,
        )
        result = asyncio.run(runtime.run(
            AnalysisMode.GENERAL_TEXT,
            ParsedDocument(title="文档", raw_text="正文"),
        ))
        self.assertEqual(runner.calls, 1)
        self.assertEqual(result.execution.call_count, 1)
        self.assertTrue(result.execution.unknown_usage)
        self.assertEqual(result.policy.effective.intensity.value, "standard")

    def test_report_runtime_does_not_call_runner_after_preflight_budget_rejection(self) -> None:
        runner = _Runner()
        runtime = CrewAIRuntime(
            general_text_pipeline=GeneralTextPipeline(crew_runner=runner),
            research_paper_pipeline=None,
        )
        result = asyncio.run(runtime.run(
            AnalysisMode.GENERAL_TEXT,
            ParsedDocument(title="文档", raw_text="正文"),
            policy=ExecutionPolicyRequest(token_budget=256, max_output_tokens=256),
        ))
        self.assertEqual(runner.calls, 0)
        self.assertEqual(result.execution.stop_reason, "token_budget_exhausted")
        self.assertEqual(result.quality.status, "blocked")


if __name__ == "__main__":
    unittest.main()
