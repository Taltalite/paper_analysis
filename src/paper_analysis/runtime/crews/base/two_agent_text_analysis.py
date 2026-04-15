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


class CrewAITwoAgentTextAnalysisRunner:
    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        verbose: bool = True,
    ) -> None:
        self._llm_client = llm_client
        self._verbose = verbose

    def run(self, *, document: ParsedDocument, profile: TextAnalysisProfile) -> AnalysisResult:
        reader = self._build_reader(profile=profile, document=document)
        analyst = self._build_analyst(profile=profile, document=document)

        extract_notes_task = Task(
            description=self._build_reader_task_description(profile=profile, document=document),
            expected_output="一份仅包含原文可追溯内容、且使用指定标题的精炼中文 markdown 笔记。",
            agent=reader,
        )
        synthesize_task = Task(
            description=self._build_analyst_task_description(profile=profile, document=document),
            expected_output="一个字段键名保持兼容、字段值说明主要使用简体中文的有效 AnalysisResult 对象。",
            agent=analyst,
            output_pydantic=AnalysisResult,
        )

        result = Crew(
            agents=[reader, analyst],
            tasks=[extract_notes_task, synthesize_task],
            process=Process.sequential,
            verbose=self._verbose,
        ).kickoff()
        return self._coerce_output(result)

    def _build_reader(self, *, profile: TextAnalysisProfile, document: ParsedDocument) -> Agent:
        return Agent(
            role=f"{profile.reader_role}：{document.title or '未命名文档'}",
            goal=profile.reader_goal,
            backstory=profile.reader_backstory,
            verbose=self._verbose,
            tools=[PaperSectionExtractorTool(), PaperKeywordSearchTool()],
            allow_delegation=False,
            llm=self._build_llm(),
        )

    def _build_analyst(self, *, profile: TextAnalysisProfile, document: ParsedDocument) -> Agent:
        return Agent(
            role=f"{profile.analyst_role}：{document.title or '未命名文档'}",
            goal=profile.analyst_goal,
            backstory=profile.analyst_backstory,
            verbose=self._verbose,
            tools=[PaperKeywordSearchTool(), PaperSectionExtractorTool()],
            allow_delegation=False,
            llm=self._build_llm(),
        )

    def _build_llm(self):
        if self._llm_client is None:
            return None
        return self._llm_client.to_crewai_llm()

    @staticmethod
    def _build_reader_task_description(
        *,
        profile: TextAnalysisProfile,
        document: ParsedDocument,
    ) -> str:
        headings = "\n".join(
            f"{index}. {heading}" for index, heading in enumerate(profile.note_headings, start=1)
        )
        rules = "\n".join(f"- {rule}" for rule in profile.reader_rules)
        return (
            f'请阅读题为“{document.title or "未命名文档"}”的以下文本。\n\n'
            f"原文内容：\n{document.raw_text}\n\n"
            "只提取能够回到原文定位的事实性笔记。\n\n"
            "请输出一份精炼的 markdown 笔记，并严格使用以下标题：\n"
            f"{headings}\n\n"
            "语言与内容规则：\n"
            f"{rules}"
        )

    @staticmethod
    def _build_analyst_task_description(
        *,
        profile: TextAnalysisProfile,
        document: ParsedDocument,
    ) -> str:
        rules = "\n".join(f"- {rule}" for rule in profile.analyst_rules)
        structured_data_requirements = "\n".join(
            f"- {item}" for item in profile.structured_data_requirements
        )
        return (
            f'请基于上一任务生成的笔记，以及题为“{document.title or "未命名文档"}”的同一份文本，生成最终分析结果。\n\n'
            f"原文内容：\n{document.raw_text}\n\n"
            "你必须输出一个最终结构化分析对象，字段键名保持以下英文名称：\n"
            "- title\n"
            "- summary\n"
            "- key_points\n"
            "- limitations\n"
            "- markdown_report\n"
            "- structured_data\n\n"
            "`markdown_report` 请返回空字符串，由应用层统一渲染最终 markdown。\n"
            "`summary`、`key_points`、`limitations` 以及 `structured_data` 中的说明性内容，应统一使用自然、专业、简洁的简体中文。\n"
            "除论文标题、作者名、机构名、期刊/会议名、专业术语、模型名、数据集名、方法名、指标名、代码库名、API 名称和直接引用外，不要把整段结果写成英文。\n"
            "重要术语首次出现时，优先使用“中文解释（原文术语）”格式。\n"
            "`structured_data` 还需要满足以下场景要求：\n"
            f"{structured_data_requirements}\n\n"
            "补充规则：\n"
            f"{rules}"
        )

    @staticmethod
    def _coerce_output(result: object) -> AnalysisResult:
        structured = getattr(result, "pydantic", None)

        if structured is None and hasattr(result, "to_dict"):
            maybe_dict = result.to_dict()
            if isinstance(maybe_dict, dict):
                structured = AnalysisResult(**maybe_dict)

        if isinstance(structured, dict):
            structured = AnalysisResult(**structured)

        if not isinstance(structured, AnalysisResult):
            raise ValueError(
                "Crew 未返回结构化的 AnalysisResult。"
                "请检查最终任务的 output_pydantic 配置。"
            )

        return structured
