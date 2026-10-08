import unittest

from pydantic import ValidationError

from paper_analysis.domain.execution import (
    AnalysisIntensity,
    ExecutionPolicyRequest,
    ResolvedPolicy,
    TokenUsage,
)
from paper_analysis.domain.research import (
    BenchmarkEntry,
    BenchmarkSection,
    EvidenceRef,
    EvidenceKind,
    FigureFlow,
    FlowEdge,
    FlowNode,
    ResearchProducts,
    DomainFinding,
    StoryArchitecture,
    StoryEdge,
    StoryNode,
)


class ExecutionContractTests(unittest.TestCase):
    def test_intensity_defaults_are_explicit_and_server_limits_are_strict(self) -> None:
        light = ResolvedPolicy.resolve(ExecutionPolicyRequest(intensity=AnalysisIntensity.LIGHT))
        self.assertEqual(light.effective.token_budget, 12_000)
        self.assertEqual(light.effective.max_followups, 0)

        requested = ExecutionPolicyRequest(
            intensity=AnalysisIntensity.DEEP,
            token_budget=90_000,
            max_calls=90,
            max_output_tokens=8_000,
            timeout_seconds=600,
            max_followups=5,
            max_figures=10,
            max_visual_reviews=7,
        )
        resolved = ResolvedPolicy.resolve(requested)
        self.assertEqual(resolved.effective.token_budget, 90_000)
        self.assertEqual(resolved.effective.max_calls, 90)
        self.assertEqual(resolved.effective.max_followups, 5)
        self.assertTrue(resolved.configuration_fingerprint)
        self.assertEqual(
            resolved.model_copy(update={"configuration_fingerprint": "other"}).configuration_fingerprint,
            "other",
        )

    def test_request_and_usage_validation_distinguish_missing_values(self) -> None:
        with self.assertRaises(ValidationError):
            ExecutionPolicyRequest(token_budget=128)
        with self.assertRaises(ValidationError):
            TokenUsage(input=10, output=4, total=13)
        with self.assertRaises(ValidationError):
            TokenUsage(unknown=True, total=1)
        self.assertIsNone(TokenUsage(input=10).total)


class ResearchContractTests(unittest.TestCase):
    def test_graph_edges_must_bind_to_known_nodes(self) -> None:
        with self.assertRaises(ValidationError):
            StoryArchitecture(
                nodes=[StoryNode(node_id="n1", statement="问题")],
                edges=[StoryEdge(edge_id="e1", source="n1", target="missing", relation="支持")],
            )
        with self.assertRaises(ValidationError):
            FigureFlow(
                nodes=[FlowNode(node_id="f1", figure="Figure 1", role="结果")],
                edges=[FlowEdge(edge_id="e1", source="f1", target="f2", relation="顺序")],
            )

    def test_benchmark_and_evidence_keep_missing_data_explicit(self) -> None:
        with self.assertRaises(ValidationError):
            BenchmarkEntry(entry_id="b1", method="A", metric="accuracy", value=0.8)
        with self.assertRaises(ValidationError):
            BenchmarkSection(status="not_applicable")
        evidence = EvidenceRef(
            document_sha256="sha",
            evidence_id="p1_b1",
            kind=EvidenceKind.TEXT,
            page=1,
            block_id="p1_b1",
            excerpt="原文证据",
        )
        self.assertEqual(evidence.kind, EvidenceKind.TEXT)

    def test_research_products_reject_unknown_evidence_binding(self) -> None:
        with self.assertRaises(ValidationError):
            ResearchProducts(
                findings=[DomainFinding(
                    finding_id="f1",
                    statement="事实",
                    evidence_ids=["missing"],
                )],
            )


if __name__ == "__main__":
    unittest.main()
