from typing import List

from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from paper_analysis.state import PaperAnalysisOutput
from paper_analysis.tools.custom_tool import (
    PaperKeywordSearchTool,
    PaperSectionExtractorTool,
)


@CrewBase
class ContentCrew:
    """Two-agent crew for analyzing a single academic paper."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def reader(self) -> Agent:
        return Agent(
            config=self.agents_config["reader"],  # type: ignore[index]
            verbose=True,
            tools=[PaperSectionExtractorTool(), PaperKeywordSearchTool()],
            allow_delegation=False,
        )

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["analyst"],  # type: ignore[index]
            verbose=True,
            tools=[PaperKeywordSearchTool(), PaperSectionExtractorTool()],
            allow_delegation=False,
        )

    @task
    def extract_paper_notes_task(self) -> Task:
        return Task(
            config=self.tasks_config["extract_paper_notes_task"],  # type: ignore[index]
        )

    @task
    def synthesize_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["synthesize_analysis_task"],  # type: ignore[index]
            output_pydantic=PaperAnalysisOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )