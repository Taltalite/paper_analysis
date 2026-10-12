from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from paper_analysis.adapters.storage.qa_store import atomic_json
from paper_analysis.domain.evaluation import (
    CaseReview, ClaimReview, ReferenceCase, ReferenceClaim, ReferenceDataset,
    ReferenceEvidence, ReferencePaper, ReviewBundle,
)
from paper_analysis.domain.qa import (
    AnswerClaim, AnswerResponse, EvidenceLocation, QuestionAudit, QuestionJob, QuestionRequest, QuestionRound,
)
from paper_analysis.domain.quality import QualityReport
from paper_analysis.services.qa_evaluation import CandidateRun, EvaluationManifest
from paper_analysis.services.reference_evaluation import (
    file_sha256, prepare_candidates, score_run, validate_sources,
)


class ReferenceEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.pdf"
        import fitz

        with fitz.open() as document:
            page = document.new_page()
            page.insert_text((72, 72), "Three biological replicates were used.")
            document.save(self.source)
        self.dataset_path = self.root / "reference.json"
        self.reference_case = ReferenceCase(candidate_id="P-1", paper_id="P", question="有几个生物学重复？",
            task_kind="text", expected_status="answered", reference_answer="3 个生物学重复。",
            gold_claims=[ReferenceClaim(claim_id="G1", statement="3 个生物学重复。", basis="text", evidence_ids=["E1"])],
            gold_evidence=[ReferenceEvidence(evidence_id="E1", source_kind="text", pdf_page_1_based=1,
                verbatim_quote="Three biological replicates were used.")])
        self.dataset = ReferenceDataset(dataset_id="test", created_at=datetime.now(UTC), provenance="测试参考",
            papers={"P": ReferencePaper(source_path=str(self.source), sha256=file_sha256(self.source),
                title="测试论文", doi="10.test/reference", page_count=1)}, cases=[self.reference_case])
        atomic_json(self.dataset_path, self.dataset)
        self.candidates = self.root / "candidates.jsonl"
        prepare_candidates(self.dataset, self.candidates)
        self.run = EvaluationManifest(candidate_manifest_sha256=file_sha256(self.candidates))
        self.run_path = self.root / "manifest.json"
        self.review_path = self.root / "review.json"

    def save_answer(self, *, claims: list[AnswerClaim] | None = None, status: str = "answered") -> AnswerResponse:
        request = QuestionRequest(question=self.reference_case.question)
        answer = AnswerResponse(request=request, status=status, answer="测试回答",
            claims=claims if claims is not None else [AnswerClaim(claim_id="A1", statement="3 个生物学重复。",
                basis="text", evidence_ids=["p1_b1"])], quality=QualityReport(status="passed"),
            document_sha256=self.dataset.papers["P"].sha256)
        job = QuestionJob(id=answer.id, request=request, filename="source.pdf", status="completed",
            document_sha256=answer.document_sha256)
        directory = self.root / "questions" / str(answer.id)
        atomic_json(directory / "answer.json", answer)
        atomic_json(directory / "job.json", job)
        atomic_json(directory / "audit-1.json", QuestionAudit(job_id=answer.id, attempt=1,
            execution_kind="offline_test", document_sha256=answer.document_sha256,
            rounds=[QuestionRound(index=0, evidence=[EvidenceLocation(evidence_id="p1_b1", kind="text", page=1,
                excerpt="Three biological replicates were used.")])]))
        self.run.results = [CandidateRun(candidate_id="P-1", answer_id=str(answer.id), execution="offline_test")]
        atomic_json(self.run_path, self.run)
        return answer

    def save_review(self, answer: AnswerResponse, **updates: object) -> None:
        case = CaseReview(candidate_id="P-1", answer_id=str(answer.id),
            answer_sha256=file_sha256(self.root / "questions" / str(answer.id) / "answer.json"),
            claim_reviews=[ClaimReview(answer_claim_id="A1", matched_gold_claim_ids=["G1"],
                correctness="correct", citation_correct=True, reason="原文明确为 3 个重复。")],
            uncertainty_correct=True, forbidden_inference_present=False, rationale="正确回答。")
        case = case.model_copy(update=updates)
        bundle = ReviewBundle(dataset_sha256=file_sha256(self.dataset_path), run_id=str(self.run.run_id),
            reviewer="独立测试评价者", review_kind="ai_assisted", cases=[case])
        atomic_json(self.review_path, bundle)

    def test_source_validation_and_no_reference_leak_to_candidates(self) -> None:
        self.assertEqual(validate_sources(self.dataset)["quotes_validated"], 1)
        candidate = json.loads(self.candidates.read_text())
        self.assertNotIn("gold_claims", candidate)
        self.assertNotIn("reference_answer", candidate)
        self.source.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "指纹"):
            validate_sources(self.dataset)

    def test_unknown_gold_link_and_text_masquerading_as_visual_rejected(self) -> None:
        data = self.reference_case.model_dump()
        data["gold_claims"][0]["evidence_ids"] = ["unknown"]
        with self.assertRaises(ValidationError):
            ReferenceCase.model_validate(data)
        data = self.reference_case.model_dump()
        data["gold_claims"][0]["basis"] = "visual"
        with self.assertRaises(ValidationError):
            ReferenceCase.model_validate(data)

    def test_refusal_does_not_make_claim_precision_one_hundred_percent(self) -> None:
        self.reference_case.expected_status = "refused"
        self.reference_case.gold_claims = []
        self.reference_case.reference_answer = "缺证据拒答。"
        self.dataset.cases = [self.reference_case]
        atomic_json(self.dataset_path, self.dataset)
        answer = self.save_answer(claims=[], status="refused")
        self.save_review(answer, claim_reviews=[])
        report = score_run(self.dataset_path, self.run_path, review_path=self.review_path)
        self.assertIsNone(report.metrics["claim_correctness"].value)
        self.assertEqual(report.metrics["correct_refusal"].value, 1)
        self.assertIsNone(report.metrics["complete_answerable"].value)

    def test_unreviewed_answer_has_no_semantic_score(self) -> None:
        self.save_answer()
        report = score_run(self.dataset_path, self.run_path)
        self.assertIsNone(report.metrics["claim_correctness"].value)
        self.assertEqual(report.metrics["text_evidence_recall"].value, 1)
        self.assertIsNone(report.cases[0].complete)
        self.assertEqual(report.optimization_priority, [])

    def test_correct_review_and_hash_bound_artifact(self) -> None:
        answer = self.save_answer()
        self.save_review(answer)
        report = score_run(self.dataset_path, self.run_path, review_path=self.review_path)
        self.assertEqual(report.metrics["required_claim_recall"].value, 1)
        self.assertTrue(report.cases[0].complete)
        answer.answer = "回答已改变"
        atomic_json(self.root / "questions" / str(answer.id) / "answer.json", answer)
        with self.assertRaisesRegex(ValueError, "回答已改变"):
            score_run(self.dataset_path, self.run_path, review_path=self.review_path)

    def test_unreviewed_claim_is_rejected(self) -> None:
        answer = self.save_answer()
        self.save_review(answer, claim_reviews=[])
        with self.assertRaisesRegex(ValueError, "所有输出主张"):
            score_run(self.dataset_path, self.run_path, review_path=self.review_path)

    def test_false_citation_and_optional_extra_claim_are_not_hidden(self) -> None:
        answer = self.save_answer()
        self.save_review(answer, claim_reviews=[ClaimReview(answer_claim_id="A1", matched_gold_claim_ids=["G1"],
            correctness="correct", citation_correct=False, reason="主张正确但错误引用另一段。")],
            primary_error="citation", rationale="引用错误。")
        report = score_run(self.dataset_path, self.run_path, review_path=self.review_path)
        self.assertEqual(report.metrics["claim_correctness"].value, 1)
        self.assertEqual(report.metrics["citation_correctness"].value, 0)
        self.assertFalse(report.cases[0].complete)
        self.assertEqual(report.error_counts, {"citation": 1})

    def test_primary_error_count_does_not_double_count_secondary_errors(self) -> None:
        answer = self.save_answer(claims=[], status="refused")
        self.save_review(answer, claim_reviews=[], primary_error="retrieval", secondary_errors=["status"],
            rationale="原文有答案，但审计未取得必要证据。")
        report = score_run(self.dataset_path, self.run_path, review_path=self.review_path)
        self.assertEqual(report.error_counts, {"retrieval": 1})
        self.assertEqual(report.error_denominator, 1)
        self.assertEqual(report.optimization_priority, ["retrieval"])

    def test_failed_run_stays_in_answerable_denominator(self) -> None:
        self.run.results = [CandidateRun(candidate_id="P-1", execution="execution_failed")]
        atomic_json(self.run_path, self.run)
        atomic_json(self.review_path, ReviewBundle(dataset_sha256=file_sha256(self.dataset_path),
            run_id=str(self.run.run_id), reviewer="独立测试评价者", review_kind="ai_assisted",
            cases=[CaseReview(candidate_id="P-1", rationale="工作进程失败。", primary_error="execution")]))
        report = score_run(self.dataset_path, self.run_path, review_path=self.review_path)
        self.assertEqual(report.metrics["complete_answerable"].denominator, 1)
        self.assertEqual(report.metrics["required_claim_recall"].value, 0)
        self.assertEqual(report.error_counts, {"execution": 1})

    def test_run_and_dataset_hash_mismatch_rejected(self) -> None:
        answer = self.save_answer()
        self.save_review(answer)
        self.run.candidate_manifest_sha256 = "a" * 64
        atomic_json(self.run_path, self.run)
        with self.assertRaisesRegex(ValueError, "候选清单"):
            score_run(self.dataset_path, self.run_path, review_path=self.review_path)

    def test_review_requires_status_and_boundary_judgments(self) -> None:
        answer = self.save_answer()
        self.save_review(answer, uncertainty_correct=None)
        with self.assertRaisesRegex(ValueError, "不确定性"):
            score_run(self.dataset_path, self.run_path, review_path=self.review_path)

    def test_full_figure_visual_input_covers_requested_panel(self) -> None:
        from paper_analysis.services.reference_evaluation import _retrieved

        case = ReferenceCase(candidate_id="V-1", paper_id="P", question="读取子图 a 标签。",
            task_kind="visual", figure="1", panel="a", expected_status="answered", reference_answer="标签是 X。",
            gold_claims=[ReferenceClaim(claim_id="G", statement="标签是 X。", basis="visual", evidence_ids=["V"])],
            gold_evidence=[ReferenceEvidence(evidence_id="V", source_kind="vision", pdf_page_1_based=1,
                figure="1", panel="a", visual_observation="子图 a 标签 X。")])
        audit = QuestionAudit(job_id=uuid4(),
            attempt=1, execution_kind="offline_test", document_sha256=file_sha256(self.source), rounds=[QuestionRound(index=0,
                evidence=[EvidenceLocation(evidence_id="V1", kind="vision", page=1, figure="Figure 1", panel=None,
                    excerpt="完整图像输入", image_pages=[1])])])
        self.assertEqual(_retrieved(case, audit), ["V"])
        audit.rounds[0].evidence[0].panel = "b"
        self.assertEqual(_retrieved(case, audit), [])

    def test_text_answer_cannot_satisfy_direct_visual_reference(self) -> None:
        self.reference_case.gold_claims[0].basis = "visual"
        self.reference_case.gold_evidence = [ReferenceEvidence(evidence_id="E1", source_kind="vision",
            pdf_page_1_based=1, figure="1", panel="a", visual_observation="图中三个重复点。")]
        atomic_json(self.dataset_path, self.dataset)
        answer = self.save_answer()
        self.save_review(answer)
        with self.assertRaisesRegex(ValueError, "依据类型"):
            score_run(self.dataset_path, self.run_path, review_path=self.review_path)

    def test_non_finite_bbox_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ReferenceEvidence(evidence_id="bad", source_kind="text", pdf_page_1_based=1,
                verbatim_quote="Some text", bbox=[0, 0, float("inf"), 50])


if __name__ == "__main__":
    unittest.main()
