from paper_analysis.flow import PaperAnalysisFlow


def kickoff():
    flow = PaperAnalysisFlow()
    flow.kickoff(
        inputs={
            "input_path": "input/sample_paper.txt",
            "output_markdown_path": "output/report.md",
            "output_json_path": "output/report.json",
        }
    )


def plot():
    flow = PaperAnalysisFlow()
    flow.plot()


def run_with_trigger():
    flow = PaperAnalysisFlow()
    flow.kickoff(
        inputs={
            "input_path": "input/sample_paper.txt",
            "output_markdown_path": "output/report.md",
            "output_json_path": "output/report.json",
        }
    )