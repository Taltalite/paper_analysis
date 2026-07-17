from __future__ import annotations

import json
import logging
import re
from typing import Protocol

from crewai import Agent, Crew, Process, Task

from paper_analysis.adapters.llm.base import LLMClient
from paper_analysis.domain.models import (
    ClaimEvidence,
    FactCheckBatch,
    FactCheckItem,
    FigureAnalysis,
    FigureEvidence,
)
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.tools import PaperKeywordSearchTool, PaperSectionExtractorTool


logger = logging.getLogger(__name__)


class FactCheckRunner(Protocol):
    def run(
        self,
        *,
        document: ParsedDocument,
        analysis_result: AnalysisResult,
        figure_analyses: list[FigureAnalysis],
        figure_evidence: list[FigureEvidence],
    ) -> FactCheckBatch:
        ...


class CrewAIFactCheckRunner:
    _VERDICTS = {
        "supported",
        "partially_supported",
        "unsupported",
        "conflicting",
        "unverifiable",
    }

    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        verbose: bool = True,
    ) -> None:
        self._llm_client = llm_client
        self._verbose = verbose

    def run(
        self,
        *,
        document: ParsedDocument,
        analysis_result: AnalysisResult,
        figure_analyses: list[FigureAnalysis],
        figure_evidence: list[FigureEvidence],
    ) -> FactCheckBatch:
        claims = self._collect_claims(
            analysis_result=analysis_result,
            figure_analyses=figure_analyses,
        )
        if not claims:
            return FactCheckBatch(overall_assessment="没有可供核验的明确主张。")
        if self._llm_client is None:
            return self._fallback_batch(claims=claims, reason="未配置 LLM，未执行语义事实检查")

        agent = Agent(
            role=f"论文事实检查助手：{document.title or '未命名文档'}",
            goal="逐条核验正文与图表分析产生的主张，并给出证据引用、判定和不确定性。",
            backstory=(
                "你是一名独立的学术事实检查员。你不重新撰写论文摘要，"
                "只判断主张是否被当前论文正文、图注和图表证据支持。"
            ),
            verbose=self._verbose,
            tools=[PaperKeywordSearchTool(), PaperSectionExtractorTool()],
            allow_delegation=False,
            llm=self._llm_client.to_crewai_llm(),
        )
        task = Task(
            description=self._build_task_description(
                document=document,
                claims=claims,
                figure_evidence=figure_evidence,
            ),
            expected_output=(
                "严格的 FactCheckBatch JSON；每条主张使用 supported、partially_supported、"
                "unsupported、conflicting 或 unverifiable 判定。"
            ),
            agent=agent,
            output_pydantic=FactCheckBatch,
        )
        try:
            result = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=self._verbose,
            ).kickoff()
            return self._coerce_output(result=result, claims=claims)
        except Exception as exc:
            logger.warning("事实检查 agent 执行失败，回退到未核验结果：%s", exc)
            return self._fallback_batch(claims=claims, reason=str(exc))

    @classmethod
    def _collect_claims(
        cls,
        *,
        analysis_result: AnalysisResult,
        figure_analyses: list[FigureAnalysis],
    ) -> list[ClaimEvidence]:
        collected: list[ClaimEvidence] = []
        raw_claims = analysis_result.structured_data.get("claims")
        if isinstance(raw_claims, list):
            for item in raw_claims:
                if not isinstance(item, dict):
                    continue
                try:
                    claim = ClaimEvidence.model_validate(item)
                except Exception:
                    continue
                if claim.statement:
                    collected.append(claim)

        if not collected:
            fallback_values = [analysis_result.summary, *analysis_result.key_points]
            extracted_notes = analysis_result.structured_data.get("extracted_notes")
            if isinstance(extracted_notes, dict):
                fallback_values.extend(
                    str(extracted_notes.get(key, ""))
                    for key in ("research_problem", "core_method", "main_results")
                )
            for index, value in enumerate(fallback_values, start=1):
                statement = cls._sanitize_text(value, max_length=400)
                if statement:
                    collected.append(
                        ClaimEvidence(
                            claim_id=f"text-{index}",
                            statement=statement,
                            category="text_analysis",
                        )
                    )

        start_index = len(collected) + 1
        for offset, analysis in enumerate(figure_analyses):
            statement = cls._sanitize_text(analysis.claimed_conclusion, max_length=400)
            if not statement or statement == "不足以判断":
                continue
            collected.append(
                ClaimEvidence(
                    claim_id=f"figure-{start_index + offset}",
                    statement=statement,
                    category="figure_claim",
                    source_sections=[analysis.figure_id] if analysis.figure_id else [],
                    evidence=analysis.main_observations[:3],
                    confidence=analysis.confidence,
                )
            )
        return collected[:20]

    @classmethod
    def _build_task_description(
        cls,
        *,
        document: ParsedDocument,
        claims: list[ClaimEvidence],
        figure_evidence: list[FigureEvidence],
    ) -> str:
        source_text = cls._source_excerpt(document)
        claims_json = json.dumps(
            [claim.model_dump(mode="json") for claim in claims],
            ensure_ascii=False,
            indent=2,
        )
        figures_json = json.dumps(
            [evidence.model_dump(mode="json") for evidence in figure_evidence],
            ensure_ascii=False,
            indent=2,
        )
        return (
            f'请核验题为“{document.title or "未命名文档"}”的分析主张。\n\n'
            "判定含义：\n"
            "- supported：证据直接且充分支持\n"
            "- partially_supported：部分有证据，但范围或强度被扩大\n"
            "- unsupported：当前材料没有支持证据\n"
            "- conflicting：当前材料存在相反证据\n"
            "- unverifiable：材料不足以判断\n\n"
            "待核验主张：\n"
            f"{claims_json}\n\n"
            "图表证据：\n"
            f"{figures_json}\n\n"
            "论文证据摘录：\n"
            f"{source_text}\n\n"
            "逐条输出 claim_id、claim、claim_source、verdict、evidence_refs、rationale、confidence。\n"
            "evidence_refs 应引用章节名、Figure ID 或简短原文片段；不要引入当前材料之外的事实。\n"
            "说明性内容使用简体中文，最终只输出 JSON。"
        )

    @staticmethod
    def _source_excerpt(document: ParsedDocument) -> str:
        priority = (
            "abstract",
            "introduction",
            "method",
            "experimental_setup",
            "results",
            "discussion",
            "conclusion",
        )
        chunks: list[str] = []
        total = 0
        for section in priority:
            content = document.sections.get(section, "").strip()
            if not content:
                continue
            chunk = f"## {section}\n{content}"
            remaining = 16000 - total
            if remaining <= 0:
                break
            chunks.append(chunk[:remaining])
            total += min(len(chunk), remaining)
        return "\n\n".join(chunks) or document.raw_text[:16000]

    @classmethod
    def _coerce_output(
        cls,
        *,
        result: object,
        claims: list[ClaimEvidence],
    ) -> FactCheckBatch:
        structured = getattr(result, "pydantic", None)
        if isinstance(structured, FactCheckBatch):
            return cls._sanitize_batch(structured)
        if isinstance(structured, dict):
            return cls._sanitize_batch(FactCheckBatch.model_validate(structured))
        maybe_dict = getattr(result, "to_dict", None)
        if callable(maybe_dict):
            payload = maybe_dict()
            if isinstance(payload, dict):
                return cls._sanitize_batch(FactCheckBatch.model_validate(payload))
        return cls._fallback_batch(claims=claims, reason="模型未返回结构化事实检查结果")

    @classmethod
    def _sanitize_batch(cls, batch: FactCheckBatch) -> FactCheckBatch:
        checks: list[FactCheckItem] = []
        for item in batch.checks[:20]:
            verdict = cls._sanitize_text(item.verdict, max_length=40).lower()
            if verdict not in cls._VERDICTS:
                verdict = "unverifiable"
            checks.append(
                FactCheckItem(
                    claim_id=cls._sanitize_text(item.claim_id, max_length=60),
                    claim=cls._sanitize_text(item.claim, max_length=400),
                    claim_source=cls._sanitize_text(item.claim_source, max_length=40) or "text",
                    verdict=verdict,
                    evidence_refs=[
                        cls._sanitize_text(value, max_length=240)
                        for value in item.evidence_refs[:6]
                        if cls._sanitize_text(value, max_length=240)
                    ],
                    rationale=cls._sanitize_text(item.rationale, max_length=400),
                    confidence=cls._sanitize_text(item.confidence, max_length=40) or "不足以判断",
                )
            )
        return FactCheckBatch(
            checks=checks,
            overall_assessment=cls._sanitize_text(batch.overall_assessment, max_length=600),
        )

    @classmethod
    def _fallback_batch(
        cls,
        *,
        claims: list[ClaimEvidence],
        reason: str,
    ) -> FactCheckBatch:
        rendered_reason = cls._sanitize_text(reason, max_length=240)
        return FactCheckBatch(
            checks=[
                FactCheckItem(
                    claim_id=claim.claim_id,
                    claim=claim.statement,
                    claim_source=("figure" if claim.category == "figure_claim" else "text"),
                    verdict="unverifiable",
                    evidence_refs=[*claim.source_sections, *claim.evidence][:6],
                    rationale=f"当前未完成语义核验：{rendered_reason}",
                    confidence="不足以判断",
                )
                for claim in claims
            ],
            overall_assessment=f"事实检查未完整执行：{rendered_reason}",
        )

    @staticmethod
    def _sanitize_text(value: object, *, max_length: int) -> str:
        text = "" if value is None else str(value)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_length].strip()
