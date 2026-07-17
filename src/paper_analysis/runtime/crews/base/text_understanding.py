from __future__ import annotations

from typing import Protocol

from crewai import Agent, Crew, Process, Task

from paper_analysis.adapters.llm.base import LLMClient
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.pipelines.profiles import TextAnalysisProfile
from paper_analysis.tools import PaperKeywordSearchTool, PaperSectionExtractorTool


class TextAnalysisCrewRunner(Protocol):
    def run(self, *, document: ParsedDocument, profile: TextAnalysisProfile) -> AnalysisResult:
        ...


class CrewAITextUnderstandingRunner:
    """Single-agent text understanding runner with evidence-oriented output."""

    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        verbose: bool = True,
    ) -> None:
        self._llm_client = llm_client
        self._verbose = verbose

    def run(self, *, document: ParsedDocument, profile: TextAnalysisProfile) -> AnalysisResult:
        crew = self._build_crew(document=document, profile=profile)
        result = crew.kickoff()
        return self._coerce_output(result)

    async def arun(self, *, document: ParsedDocument, profile: TextAnalysisProfile) -> AnalysisResult:
        crew = self._build_crew(document=document, profile=profile)
        result = await crew.kickoff_async()
        return self._coerce_output(result)

    def _build_crew(self, *, document: ParsedDocument, profile: TextAnalysisProfile) -> Crew:
        agent = Agent(
            role=f"{profile.analyst_role}：{document.title or '未命名文档'}",
            goal=(
                "一次完成源文本理解、事实性要点提取与结构化综合，"
                "并为重要判断保留可供事实检查的原文证据。"
            ),
            backstory=(
                "你是一名严谨的研究分析助手。你会先区分原文事实、作者主张与分析评价，"
                "再输出结构化结果，不虚构缺失信息。"
            ),
            verbose=self._verbose,
            tools=[PaperSectionExtractorTool(), PaperKeywordSearchTool()],
            allow_delegation=False,
            llm=self._build_llm(),
        )
        task = Task(
            description=self._build_task_description(
                profile=profile,
                document=document,
            ),
            expected_output=(
                "一个有效 AnalysisResult；研究论文模式下 structured_data 还包含可追溯的 claims 列表。"
            ),
            agent=agent,
            output_pydantic=AnalysisResult,
        )
        return Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=self._verbose,
        )

    def _build_llm(self):
        if self._llm_client is None:
            return None
        return self._llm_client.to_crewai_llm()

    @staticmethod
    def _build_task_description(
        *,
        profile: TextAnalysisProfile,
        document: ParsedDocument,
    ) -> str:
        structured_requirements = "\n".join(
            f"- {item}" for item in profile.structured_data_requirements
        )
        rules = "\n".join(
            f"- {item}" for item in (*profile.reader_rules, *profile.analyst_rules)
        )
        evidence_section = CrewAITextUnderstandingRunner._build_evidence_section(document)
        return (
            f'请理解并分析题为“{document.title or "未命名文档"}”的文本。\n\n'
            f"原文内容：\n{document.raw_text}\n\n"
            f"{evidence_section}"
            "请在一次分析中完成：\n"
            "- 提取元数据、研究问题、方法、实验设置和主要结果\n"
            "- 总结创新点、优点、局限性和复现信息\n"
            "- 区分原文事实、作者主张和分析评价\n"
            "- 为重要 claim 保留 source_sections 与简短 evidence 原文片段\n\n"
            "输出 AnalysisResult，字段键名为 title、summary、key_points、limitations、"
            "markdown_report、structured_data。markdown_report 返回空字符串，由应用层渲染。\n\n"
            "structured_data 要求：\n"
            f"{structured_requirements}\n\n"
            "规则：\n"
            f"{rules}\n"
            "claims 中每条证据必须能够回到当前输入定位；没有证据的判断不要写成已证实事实。"
            "每条核心 claim 必须在 evidence_ids 字段引用可用的证据 ID；"
            "确实无法定位证据的 claim，将 evidence_ids 留空并在 confidence 中标注“低”。"
        )

    @staticmethod
    def _build_evidence_section(document: ParsedDocument) -> str:
        evidence_map = document.metadata.get("evidence_map")
        if not isinstance(evidence_map, dict):
            return ""
        section_ids = evidence_map.get("sections")
        figure_ids = evidence_map.get("figures")
        if not section_ids and not figure_ids:
            return ""
        lines = ["可用证据 ID（claims 的 evidence_ids 字段应引用这些 ID）："]
        for section_key, evidence_id in (section_ids or {}).items():
            lines.append(f"- {evidence_id} = 章节 {section_key}")
        for figure_id in figure_ids or []:
            lines.append(f"- {figure_id} = 图表证据 ID")
        return "\n".join(lines) + "\n\n"

    @staticmethod
    def _coerce_output(result: object) -> AnalysisResult:
        structured = getattr(result, "pydantic", None)
        if structured is None and hasattr(result, "to_dict"):
            payload = result.to_dict()
            if isinstance(payload, dict):
                structured = payload
        if isinstance(structured, dict):
            structured = AnalysisResult.model_validate(structured)
        if not isinstance(structured, AnalysisResult):
            raise ValueError("文本理解 agent 未返回有效的 AnalysisResult。")
        return structured
