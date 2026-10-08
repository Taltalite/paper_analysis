"""审核复现；不修改业务代码、不调用真实模型。"""
import asyncio
import json
from pathlib import Path
from unittest.mock import patch

from paper_analysis.adapters.llm.openai_compatible import OpenAICompatibleLLM
from paper_analysis.adapters.parser.mcp_figure_semantics import NoopFigureSemanticExtractor
from paper_analysis.domain.execution import ExecutionPolicyRequest, ResolvedPolicy, TokenUsage
from paper_analysis.domain.models import ClaimEvidence, FactCheckBatch, FigureMetadata
from paper_analysis.domain.qa import QuestionRequest
from paper_analysis.domain.quality import QualityReport
from paper_analysis.domain.schemas import AnalysisResult, ParsedDocument
from paper_analysis.runtime.budget import BudgetLedger
from paper_analysis.runtime.pipelines.question_answer import QuestionAnswerPipeline
from paper_analysis.runtime.pipelines.research_paper_report import ResearchPaperReportRenderer
from paper_analysis.runtime.pipelines.research_products import build_research_products
from test_question_answer import FakeRunner, FakeChecker, document

ROOT = Path(__file__).parent
checks = []


def record(name, passed, details):
    checks.append({"case": name, "passed": passed, "details": details})


class LeakingRunner(FakeRunner):
    def run(self, **kwargs):
        result = super().run(**kwargs)
        result.uncertainties = ["未核验标签断言：FAKE_LABEL_999"]
        return result


answer = QuestionAnswerPipeline(runner=LeakingRunner(), checker=FakeChecker(),
    vision=NoopFigureSemanticExtractor()).run(document=document(),
    request=QuestionRequest(question="实验重复数？", max_followups=0))
record("uncertainties_must_not_leak_unverified_assertion",
       "FAKE_LABEL_999" not in answer.model_dump_json(),
       {"status": answer.status, "uncertainties": answer.uncertainties})

doc = ParsedDocument(title="Synthetic benchmark", sections={"results": "No benchmark values reported."},
    section_order=["results"], metadata={"document_sha256": "synthetic",
    "evidence_map": {"sections": {"results": "S1"}},
    "ordered_blocks": [{"block_id": "p1_b1", "page_number": 1, "text": "No benchmark values reported."}]})
result = AnalysisResult(structured_data={"claims": [ClaimEvidence(claim_id="rejected",
    statement="UNSUPPORTED_CLAIM_999", evidence_ids=["p1_b1"]).model_dump()],
    "benchmark": {"status": "available", "entries": [{"method": "InventedMethod",
    "metric": "accuracy", "value": 99.9, "value_raw": "99.9", "value_source": "explicit",
    "evidence_ids": ["missing-evidence"]}]}}, quality=QualityReport(status="blocked"))
markdown = ResearchPaperReportRenderer().render(source_document=doc, result=result,
    selected_sections=["results"], figure_evidence=[], figure_analyses=[], fact_checks=FactCheckBatch())
ROOT.joinpath("unverified-report.md").write_text(markdown)
details = markdown.split("### 11.4 细节证据")[1].split("### 11.5")[0]
benchmark = markdown.split("### 11.5 Benchmark")[1].split("## 附录")[0]
record("rejected_claim_not_in_unlabelled_evidence_matrix", "UNSUPPORTED_CLAIM_999" not in details, details.strip())
record("benchmark_requires_verified_evidence", "InventedMethod" not in benchmark, benchmark.strip())

accepted = AnalysisResult(structured_data={"claims": [ClaimEvidence(claim_id="c1", statement="Source statement",
    evidence_ids=["S1"]).model_dump()]}, quality=QualityReport(accepted_claim_ids=["c1"]))
products = build_research_products(document=doc, result=accepted, figure_evidence=[], figure_analyses=[])
record("accepted_section_evidence_preserved", products.findings[0].evidence_ids == ["S1"],
       products.findings[0].model_dump(mode="json"))

policy = ResolvedPolicy.resolve(ExecutionPolicyRequest(max_calls=1, max_output_tokens=64))
ledger = BudgetLedger(job_id="probe", attempt=1, policy=policy.effective)
internal_calls = []
def multi_call(**kwargs):
    internal_calls.extend(["provider-call-1", "provider-call-2", "provider-call-3"])
    return "ok"
QuestionAnswerPipeline._run_text_stage(multi_call, context=ledger, stage="qa", role="qa", model="fake")
record("max_calls_applies_inside_text_stage", len(internal_calls) <= 1,
       {"simulated_internal_calls": len(internal_calls), "ledger_calls": ledger.summary().call_count})

client = OpenAICompatibleLLM(model="fake", api_key="test-key", base_url="https://example.invalid/v1",
    vision_model="fake-vision")
with patch("paper_analysis.adapters.llm.openai_compatible.LLM") as llm:
    client.to_crewai_llm()
    params = llm.call_args.kwargs
record("text_adapter_enforces_output_limit", "max_tokens" in params or "max_completion_tokens" in params,
       {"parameter_names": sorted(params)})

ledger = BudgetLedger(job_id="partial-usage", attempt=1, policy=policy.effective)
res = ledger.reserve(input_tokens=100, stage="vision", role="vision", model="fake", endpoint_id="fake")
ledger.mark_sent(res)
ledger.settle(res, usage=TokenUsage(input=50))
record("partial_provider_usage_is_retained", ledger.summary().calls[0].usage is not None,
       ledger.summary().model_dump(mode="json"))

good = QuestionAnswerPipeline(runner=FakeRunner(), checker=FakeChecker(),
    vision=NoopFigureSemanticExtractor()).run(document=document(),
    request=QuestionRequest(question="实验重复数？", max_followups=0))
record("offline_qa_happy_path", good.status == "answered" and bool(good.evidence), good.status)
missing = QuestionAnswerPipeline(runner=FakeRunner(), checker=FakeChecker(),
    vision=NoopFigureSemanticExtractor()).run(document=document(),
    request=QuestionRequest(question="Figure 99a?", figure="99", panel="a"))
record("missing_figure_refused", missing.status == "refused", missing.stop_reason)
ROOT.joinpath("smoke.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2))
print(json.dumps({"cases": len(checks), "passed": sum(x["passed"] for x in checks),
                  "failed": [x["case"] for x in checks if not x["passed"]]}, ensure_ascii=False))
