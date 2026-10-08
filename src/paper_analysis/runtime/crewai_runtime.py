from __future__ import annotations

import inspect
from pathlib import Path

from paper_analysis.domain.enums import AnalysisMode
from paper_analysis.domain.execution import ExecutionPolicyRequest, ResolvedPolicy
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.domain.quality import QualityReport
from paper_analysis.runtime.budget import BudgetExceededError, BudgetLedger, DeadlineExceededError
from paper_analysis.runtime.pipelines.general_text import GeneralTextPipeline
from paper_analysis.runtime.pipelines.research_paper import ResearchPaperPipeline


class CrewAIRuntime:
    def __init__(
        self,
        *,
        general_text_pipeline: GeneralTextPipeline,
        research_paper_pipeline: ResearchPaperPipeline,
    ) -> None:
        self._general_text_pipeline = general_text_pipeline
        self._research_paper_pipeline = research_paper_pipeline

    async def run(self, mode: AnalysisMode, document: ParsedDocument,
                  policy: ResolvedPolicy | ExecutionPolicyRequest | None = None) -> AnalysisResult:
        resolved = policy if isinstance(policy, ResolvedPolicy) else ResolvedPolicy.resolve(policy)
        job_id = str(document.metadata.get("job_id") or document.metadata.get("document_sha256") or "analysis")
        try:
            attempt = max(1, int(document.metadata.get("attempt", 1)))
        except (TypeError, ValueError):
            attempt = 1
        ledger = BudgetLedger(job_id=job_id, attempt=attempt, policy=resolved.effective, path=Path(document.metadata["budget_path"]) if document.metadata.get("budget_path") else None)
        stop_reason = "completed"
        try:
            if mode == AnalysisMode.GENERAL_TEXT:
                result = await self._invoke_pipeline(
                    self._general_text_pipeline, document, resolved, ledger
                )
            elif mode == AnalysisMode.RESEARCH_PAPER:
                result = await self._invoke_pipeline(
                    self._research_paper_pipeline, document, resolved, ledger
                )
            else:
                raise ValueError(f"Unsupported mode: {mode}")
        except (BudgetExceededError, DeadlineExceededError) as exc:
            stop_reason = exc.reason.value
            result = AnalysisResult(
                title=document.title,
                summary="执行预算不足，未发布未经核验的完整分析结果。",
                markdown_report=(
                    "# 文献分析未完成\n\n"
                    "执行预算或调用上限已达到，系统未发布未经核验的完整结论。\n\n"
                    f"停止原因：`{stop_reason}`。请调整策略后重新提交任务。"
                ),
                quality=QualityReport(status="blocked"),
                structured_data={"execution_stop_reason": stop_reason},
            )
        except Exception:
            if not ledger.stop_reason:
                raise
            result = AnalysisResult(title=document.title, summary="执行预算或时限已达到。",
                markdown_report="# 分析未完成\n\n执行预算或时限已达到，未交付未核验内容。", quality=QualityReport(status="blocked"))
        result.policy = resolved
        result.execution = ledger.summary(stop_reason=ledger.stop_reason or result.structured_data.get("execution_stop_reason", stop_reason))
        if ledger.path:
            from paper_analysis.adapters.storage.qa_store import atomic_json
            atomic_json(ledger.path, result.execution)
        return result

    @staticmethod
    async def _invoke_pipeline(pipeline, document, policy, execution_context):  # noqa: ANN001
        run = pipeline.run
        parameters = inspect.signature(run).parameters
        kwargs = {}
        if "policy" in parameters:
            kwargs["policy"] = policy
        if "execution_context" in parameters:
            kwargs["execution_context"] = execution_context
        return await run(document, **kwargs)
