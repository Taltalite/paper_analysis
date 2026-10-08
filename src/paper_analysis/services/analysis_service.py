from __future__ import annotations

import inspect
from pathlib import Path

from paper_analysis.adapters.parser.base import DocumentParser
from paper_analysis.domain.execution import ExecutionPolicyRequest, ResolvedPolicy
from paper_analysis.domain.enums import AnalysisMode
from paper_analysis.domain.schemas import AnalysisExecution, AnalysisResult, ParsedDocument
from paper_analysis.runtime.crewai_runtime import CrewAIRuntime


class AnalysisService:
    def __init__(
        self,
        *,
        text_parser: DocumentParser,
        pdf_parser: DocumentParser,
        runtime: CrewAIRuntime,
    ) -> None:
        self._text_parser = text_parser
        self._pdf_parser = pdf_parser
        self._runtime = runtime

    async def parse_file(self, path: Path) -> ParsedDocument:
        parser = self._pdf_parser if path.suffix.lower() == ".pdf" else self._text_parser
        return await parser.parse(path)

    async def analyze_document(
        self,
        document: ParsedDocument,
        mode: AnalysisMode,
        policy: ExecutionPolicyRequest | ResolvedPolicy | None = None,
    ) -> AnalysisResult:
        resolved = policy if isinstance(policy, ResolvedPolicy) else ResolvedPolicy.resolve(policy)
        run = self._runtime.run
        if "policy" in inspect.signature(run).parameters:
            result = await run(mode, document, policy=resolved)
        else:
            # 保留旧版 runtime/fake 的兼容性；正式 runtime 会收到并落盘策略。
            result = await run(mode, document)
        result.policy = resolved
        return result

    async def analyze_file(self, path: Path, mode: AnalysisMode,
                           policy: ExecutionPolicyRequest | ResolvedPolicy | None = None) -> AnalysisExecution:
        parsed = await self.parse_file(path)
        result = await self.analyze_document(parsed, mode, policy=policy)
        return AnalysisExecution(document=parsed, result=result)
