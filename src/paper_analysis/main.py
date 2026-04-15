import os

from paper_analysis.domain.enums import AnalysisMode
from paper_analysis.flow import PaperAnalysisFlow


def kickoff():
    input_path = os.getenv("INPUT_PATH", "input/sample_paper.txt")
    output_markdown_path = os.getenv("OUTPUT_MARKDOWN_PATH", "output/report.md")
    output_json_path = os.getenv("OUTPUT_JSON_PATH", "output/report.json")
    mode = AnalysisMode(os.getenv("ANALYSIS_MODE", AnalysisMode.RESEARCH_PAPER.value))
    flow = PaperAnalysisFlow()
    flow.kickoff(
        inputs={
            "input_path": input_path,
            "output_markdown_path": output_markdown_path,
            "output_json_path": output_json_path,
            "mode": mode,
        }
    )


def plot():
    flow = PaperAnalysisFlow()
    flow.plot()


def run_with_trigger():
    input_path = os.getenv("INPUT_PATH", "input/sample_paper.txt")
    output_markdown_path = os.getenv("OUTPUT_MARKDOWN_PATH", "output/report.md")
    output_json_path = os.getenv("OUTPUT_JSON_PATH", "output/report.json")
    mode = AnalysisMode(os.getenv("ANALYSIS_MODE", AnalysisMode.RESEARCH_PAPER.value))
    flow = PaperAnalysisFlow()
    flow.kickoff(
        inputs={
            "input_path": input_path,
            "output_markdown_path": output_markdown_path,
            "output_json_path": output_json_path,
            "mode": mode,
        }
    )
