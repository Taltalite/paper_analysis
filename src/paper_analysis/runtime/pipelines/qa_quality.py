"""问答特有交付约束；语义核验仍由既有 checker 完成。"""
import re
import unicodedata

from paper_analysis.domain.qa import AnswerDraft, EvidenceLocation, QuestionRequest
from paper_analysis.domain.quality import QualityIssue, QualityReport


def normalized(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).strip('"“”')


def enforce_qa_evidence(*, draft: AnswerDraft, evidence: dict[str, EvidenceLocation],
                        request: QuestionRequest, quality: QualityReport) -> None:
    for claim in draft.claims:
        reasons: list[str] = []
        refs = [evidence[eid] for eid in claim.evidence_ids if eid in evidence]
        quotes = [normalized(q) for q in claim.evidence if len(normalized(q)) >= 12]
        if not refs or len(refs) != len(claim.evidence_ids):
            reasons.append("主张引用了不存在的证据。")
        # checker 的引文不能替代主张自身的引文；每条引文和每个来源都需对应。
        if not quotes or any(not any(q in normalized(e.excerpt) for e in refs) for q in quotes):
            reasons.append("主张自身引文未在所引证据中精确定位。")
        if any(not any(q in normalized(e.excerpt) for q in quotes) for e in refs):
            reasons.append("引用的每个来源均须有对应原文片段。")
        visuals = [e for e in refs if e.kind == "vision"]
        if claim.basis == "visual":
            if not visuals or not any(q in normalized(e.excerpt) for q in quotes for e in visuals):
                reasons.append("视觉主张必须引用真实视觉观察片段，图注不能替代读图。")
            if any(not e.image_pages or (request.panel and e.panel != request.panel.lower()) for e in visuals):
                reasons.append("视觉主张的实际页面或目标子图不匹配。")
        elif visuals:
            reasons.append("视觉观察不能伪装为原文证据。")
        elif re.search(r"(?:直接观察|读图可见|图中显示|柱高显示|曲线显示)", claim.statement) and not re.search(r"图注|正文", claim.statement):
            reasons.append("直接读图表述没有声明视觉来源。")
        if reasons:
            quality.accepted_claim_ids = [cid for cid in quality.accepted_claim_ids if cid != claim.claim_id]
            quality.issues.append(QualityIssue(code="qa_evidence_mismatch", location=claim.claim_id,
                claim_id=claim.claim_id, message="；".join(reasons)))
    quality.status = "blocked" if not quality.accepted_claim_ids else ("needs_review" if quality.issues else "passed")
    for binding in quality.bindings:
        binding.claim_ids = [cid for cid in binding.claim_ids if cid in quality.accepted_claim_ids]
        binding.released = bool(binding.claim_ids)
