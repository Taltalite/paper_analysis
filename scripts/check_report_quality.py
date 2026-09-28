"""对已有模型结果执行离线 QC，不调用 LLM；原报告保持不变。"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from paper_analysis.adapters.parser.pdf import PdfParser
from paper_analysis.adapters.parser.plain_text import PlainTextParser
from paper_analysis.adapters.storage.local_fs import LocalFilesystemArtifactStorage
from paper_analysis.domain.models import FactCheckBatch, FigureAnalysis, FigureEvidence
from paper_analysis.domain.schemas import AnalysisResult
from paper_analysis.runtime.pipelines.research_paper_report import ResearchPaperReportRenderer
from paper_analysis.services.artifact_service import ArtifactService


async def run(source: Path, report: Path, output: Path) -> None:
    result = AnalysisResult.model_validate_json(report.read_text(encoding="utf-8"))
    snapshot = result.structured_data.get("qc_draft", {})
    data = snapshot.get("structured_data", result.structured_data)
    parser = PdfParser() if source.suffix.lower() == ".pdf" else PlainTextParser()
    document = await parser.parse(source)
    result.markdown_report = ResearchPaperReportRenderer().render(
        source_document=document, result=result, selected_sections=data.get("selected_sections", []),
        figure_evidence=[FigureEvidence.model_validate(item) for item in data.get("figure_evidence", [])],
        figure_analyses=[FigureAnalysis.model_validate(item) for item in data.get("figure_analyses", [])],
        fact_checks=FactCheckBatch(checks=data.get("fact_checks", []),
                                  overall_assessment=data.get("fact_check_summary", ""),
                                  rule_flags=data.get("fact_check_rule_flags", [])),
    )
    await ArtifactService(storage=LocalFilesystemArtifactStorage()).save_analysis_result(
        markdown_path=output.with_suffix(".md"), json_path=output.with_suffix(".json"),
        result=result, document=document,
    )
    assert result.quality is not None
    print(f"QC={result.quality.status}；已核验={result.quality.checked_claims}/{result.quality.expected_claims}；"
          f"可交付={len(result.quality.accepted_claim_ids)}；问题数={len(result.quality.issues)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("output/audit-qc"))
    args = parser.parse_args()
    if args.output.with_suffix(".json").resolve() == args.report.resolve():
        parser.error("输出路径不能覆盖输入报告。")
    asyncio.run(run(args.source, args.report, args.output))


if __name__ == "__main__":
    main()
