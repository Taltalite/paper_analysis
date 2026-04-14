import json
from pathlib import Path
from typing import Any

from crewai.flow import Flow, listen, start

from paper_analysis.crews.content_crew.content_crew import ContentCrew
from paper_analysis.state import PaperAnalysisOutput, PaperAnalysisState


class PaperAnalysisFlow(Flow[PaperAnalysisState]):
    """Flow for analyzing one academic paper from a local txt/md file."""

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

        self.state.status = "input_prepared"
        print(f"Input path: {self.state.input_path}")
        return self.state.input_path

    @listen(prepare_input)
    def load_paper(self, input_path: str):
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"Paper file not found: {path}")

        raw_text = path.read_text(encoding="utf-8").strip()
        if not raw_text:
            raise ValueError(f"Paper file is empty: {path}")

        self.state.raw_text = raw_text
        self.state.paper_title_hint = self._infer_title_from_text(raw_text)
        self.state.status = "paper_loaded"

        print(f"Loaded paper. Title hint: {self.state.paper_title_hint}")
        return raw_text

    @listen(load_paper)
    def run_analysis(self, paper_text: str):
        result = ContentCrew().crew().kickoff(
            inputs={
                "paper_text": paper_text,
                "paper_title": self.state.paper_title_hint or "Unknown Paper",
            }
        )

        structured = getattr(result, "pydantic", None)

        if structured is None:
            maybe_dict: Any = None
            if hasattr(result, "to_dict"):
                maybe_dict = result.to_dict()

            if isinstance(maybe_dict, dict):
                structured = PaperAnalysisOutput(**maybe_dict)
            else:
                raise ValueError(
                    "Crew did not return a structured Pydantic output. "
                    "Check the final task's output_pydantic wiring."
                )

        if isinstance(structured, dict):
            structured = PaperAnalysisOutput(**structured)

        self.state.analysis = structured
        self.state.json_report = structured.model_dump()
        self.state.markdown_report = self._build_markdown_report(structured)
        self.state.status = "analysis_completed"

        print("Paper analysis completed.")
        return self.state.markdown_report

    @listen(run_analysis)
    def save_outputs(self, _: str):
        md_path = Path(self.state.output_markdown_path)
        json_path = Path(self.state.output_json_path)

        md_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.parent.mkdir(parents=True, exist_ok=True)

        md_path.write_text(self.state.markdown_report, encoding="utf-8")
        json_path.write_text(
            json.dumps(self.state.json_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.state.status = "done"

        print(f"Markdown report saved to: {md_path}")
        print(f"JSON report saved to: {json_path}")

        return {
            "markdown_path": str(md_path),
            "json_path": str(json_path),
        }

    @staticmethod
    def _infer_title_from_text(raw_text: str) -> str:
        for line in raw_text.splitlines():
            clean = line.strip()
            if clean:
                return clean[:200]
        return "Unknown Paper"

    @staticmethod
    def _build_markdown_report(analysis: PaperAnalysisOutput) -> str:
        authors = ", ".join(analysis.metadata.authors) if analysis.metadata.authors else "N/A"
        datasets = ", ".join(analysis.extracted_notes.datasets) if analysis.extracted_notes.datasets else "N/A"
        strengths = "\n".join(f"- {item}" for item in analysis.strengths) if analysis.strengths else "- N/A"
        limitations = "\n".join(f"- {item}" for item in analysis.limitations) if analysis.limitations else "- N/A"

        return f"""# Paper Analysis Report

## Metadata
- **Title:** {analysis.metadata.title or 'N/A'}
- **Authors:** {authors}
- **Venue:** {analysis.metadata.venue or 'N/A'}
- **Year:** {analysis.metadata.year or 'N/A'}

## Research Problem
{analysis.extracted_notes.research_problem or 'N/A'}

## Core Method
{analysis.extracted_notes.core_method or 'N/A'}

## Datasets
{datasets}

## Experimental Setup
{analysis.extracted_notes.experimental_setup or 'N/A'}

## Main Results
{analysis.extracted_notes.main_results or 'N/A'}

## Novelty
{analysis.novelty or 'N/A'}

## Strengths
{strengths}

## Limitations
{limitations}

## Reproducibility
{analysis.reproducibility or 'N/A'}

## Interview Pitch
{analysis.interview_pitch or 'N/A'}
"""


def kickoff():
    PaperAnalysisFlow().kickoff()


def plot():
    PaperAnalysisFlow().plot()


if __name__ == "__main__":
    kickoff()