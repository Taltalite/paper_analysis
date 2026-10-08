from pathlib import Path
from typing import Protocol

from paper_analysis.domain.execution_context import agent_limits

from crewai import Agent, Crew, Process, Task

from paper_analysis.adapters.llm.base import LLMClient
from paper_analysis.domain.qa import AnswerDraft, EvidenceLocation, QuestionRequest


class QuestionAnswerRunner(Protocol):
    def run(self, *, request: QuestionRequest, evidence: list[EvidenceLocation], feedback: list[str]) -> AnswerDraft: ...


class CrewAIQuestionAnswerRunner:
    request_metering = True
    def __init__(self, llm_client: LLMClient) -> None:
        self.client = llm_client

    def run(self, *, request: QuestionRequest, evidence: list[EvidenceLocation], feedback: list[str]) -> AnswerDraft:
        prompt = (Path(__file__).parents[3] / "config" / "qa_prompt.txt").read_text(encoding="utf-8")
        agent = Agent(**agent_limits(), role="生物信息与表观遗传学文献问答员", goal="仅用当前证据回答问题", backstory="你逐条引用当前论文证据，明确说明不确定性。",
                      llm=self.client.to_crewai_llm(), allow_delegation=False, verbose=False)
        task = Task(description=f"{prompt}\n问题：{request.model_dump_json()}\n证据："
                    + "\n".join(item.model_dump_json() for item in evidence)
                    + f"\n上一轮问题：{feedback}", agent=agent, output_pydantic=AnswerDraft,
                    expected_output="AnswerDraft JSON，每条主张包含唯一 claim_id、statement、evidence_ids 和原文 evidence。")
        result = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff()
        return AnswerDraft.model_validate(result.pydantic)
