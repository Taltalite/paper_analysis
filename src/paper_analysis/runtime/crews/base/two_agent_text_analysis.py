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
            expected_output=(
                "A compact markdown note sheet with the required headings and only source-grounded content."
            ),
            agent=reader,
        )
        synthesize_task = Task(
            description=self._build_analyst_task_description(profile=profile, document=document),
            expected_output="A valid AnalysisResult object.",
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
            role=f"{profile.reader_role} for {document.title or 'Untitled Document'}",
            goal=profile.reader_goal,
            backstory=profile.reader_backstory,
            verbose=self._verbose,
            tools=[PaperSectionExtractorTool(), PaperKeywordSearchTool()],
            allow_delegation=False,
            llm=self._build_llm(),
        )

    def _build_analyst(self, *, profile: TextAnalysisProfile, document: ParsedDocument) -> Agent:
        return Agent(
            role=f"{profile.analyst_role} for {document.title or 'Untitled Document'}",
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
            f'Read the following text for "{document.title or "Untitled Document"}".\n\n'
            f"TEXT:\n{document.raw_text}\n\n"
            "Extract only source-grounded notes.\n\n"
            "Produce a concise markdown note sheet with these exact headings:\n"
            f"{headings}\n\n"
            "Rules:\n"
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
            f'Use the previous task note sheet and the same text for "{document.title or "Untitled Document"}" '
            "to produce the final analysis.\n\n"
            f"TEXT:\n{document.raw_text}\n\n"
            "You must produce a final structured analysis with these fields:\n"
            "- title\n"
            "- summary\n"
            "- key_points\n"
            "- limitations\n"
            "- markdown_report\n"
            "- structured_data\n\n"
            "For `markdown_report`, return an empty string. The application layer will render the final markdown.\n"
            "For `structured_data`, follow these scenario-specific requirements:\n"
            f"{structured_data_requirements}\n\n"
            "Rules:\n"
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
                "Crew did not return a structured AnalysisResult. "
                "Check the final task output_pydantic configuration."
            )

        return structured
