import asyncio
from pathlib import Path

from crewai.flow import Flow, listen, start

from paper_analysis.domain.enums import AnalysisMode
from paper_analysis.domain.models import PaperAnalysis
from paper_analysis.domain.schemas import FileAnalysisRequest
from paper_analysis.services import (
    build_default_analysis_service,
    build_default_artifact_service,
)
from paper_analysis.state import PaperAnalysisState

_ANALYSIS_SERVICE = build_default_analysis_service()
_ARTIFACT_SERVICE = build_default_artifact_service()


class PaperAnalysisFlow(Flow[PaperAnalysisState]):
    """Thin CrewAI flow wrapper for the Phase 1 text-analysis application service."""

    @start()
    def prepare_input(self, crewai_trigger_payload: dict | None = None):
        payload = crewai_trigger_payload or {}

        self.state.input_path = payload.get("input_path", self.state.input_path)
        self.state.output_markdown_path = payload.get(
            "output_markdown_path", self.state.output_markdown_path
        )
        self.state.output_json_path = payload.get(
            "output_json_path", self.state.output_json_path
        )
        mode = payload.get("mode")
        if mode:
            self.state.mode = AnalysisMode(mode)

        self.state.status = "input_prepared"
        print(f"Input path: {self.state.input_path}")
        return FileAnalysisRequest(
            input_path=self.state.input_path,
            output_markdown_path=self.state.output_markdown_path,
            output_json_path=self.state.output_json_path,
            mode=self.state.mode,
        )

    @listen(prepare_input)
    def run_analysis(self, request: FileAnalysisRequest):
        execution = asyncio.run(
            _ANALYSIS_SERVICE.analyze_file(
                path=Path(request.input_path),
                mode=request.mode,
            )
        )

        self.state.raw_text = execution.document.raw_text
        self.state.parsed_document = execution.document
        self.state.paper_title_hint = execution.document.title
        self.state.analysis = execution.result
        self.state.json_report = execution.result.model_dump()
        self.state.markdown_report = execution.result.markdown_report
        try:
            self.state.legacy_paper_analysis = PaperAnalysis.model_validate(
                execution.result.structured_data
            )
        except Exception:
            self.state.legacy_paper_analysis = None
        self.state.status = "analysis_completed"

        print(f"Loaded text. Title hint: {self.state.paper_title_hint}")
        print("Text analysis completed.")
        return self.state.markdown_report

    @listen(run_analysis)
    def save_outputs(self, _: str):
        artifact = asyncio.run(
            _ARTIFACT_SERVICE.save_analysis_result(
                markdown_path=Path(self.state.output_markdown_path),
                json_path=Path(self.state.output_json_path),
                result=self.state.analysis,
                document=self.state.parsed_document,
            )
        )

        self.state.status = "done"

        print(f"Markdown report saved to: {artifact.markdown_report_path}")
        print(f"JSON report saved to: {artifact.json_report_path}")
        if artifact.parsed_markdown_path:
            print(f"Parsed markdown saved to: {artifact.parsed_markdown_path}")

        return {
            "markdown_path": artifact.markdown_report_path,
            "json_path": artifact.json_report_path,
            "parsed_markdown_path": artifact.parsed_markdown_path,
        }


def kickoff():
    PaperAnalysisFlow().kickoff()


def plot():
    PaperAnalysisFlow().plot()


if __name__ == "__main__":
    kickoff()
