"""直接查看实际输入页的窄核验适配器；与文本 checker 分开调用。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from paper_analysis.adapters.llm.base import VisionLLMClient
from paper_analysis.domain.qa import AnswerClaim, QuestionRequest, VisualCheckBatch
from paper_analysis.runtime.budget import BudgetLedger


class VisualClaimChecker(Protocol):
    def check(self, *, request: QuestionRequest, claims: list[AnswerClaim],
              image_paths: list[Path], execution_context: BudgetLedger | None = None) -> VisualCheckBatch: ...


class ImageClaimChecker:
    def __init__(self, client: VisionLLMClient) -> None:
        self.client = client

    def check(self, *, request: QuestionRequest, claims: list[AnswerClaim],
              image_paths: list[Path], execution_context: BudgetLedger | None = None) -> VisualCheckBatch:
        # 不把原视觉摘录或文本 checker 判定传给复核调用，避免直接复述旧判定。
        payload = {"question": request.question, "figure": request.figure, "panel": request.panel,
                   "claims": [{"claim_id": c.claim_id, "statement": c.statement} for c in claims]}
        data = json.dumps(payload, ensure_ascii=False)
        if len(data) > 12000:
            raise ValueError("视觉复核输入超过字符预算。")
        prompt = (Path(__file__).parents[2] / "config/visual_check_prompt.txt").read_text()
        raw = self.client.complete_with_images(
            prompt=prompt + "\n待核对数据：\n" + data,
            image_paths=image_paths,
            execution_context=execution_context,
            stage="visual_review",
            role="visual_checker",
        )
        raw = raw.strip()
        if raw.startswith("```") and raw.endswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return VisualCheckBatch.model_validate_json(raw)
