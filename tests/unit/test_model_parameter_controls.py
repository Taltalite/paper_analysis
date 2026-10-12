"""验证请求实际参数、预算约束和视觉缓存隔离；不调用真实模型。"""
import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx

from paper_analysis.adapters.llm.factory import create_llm_client_from_env
from paper_analysis.adapters.llm.visual_check import ImageClaimChecker
from paper_analysis.adapters.parser.multimodal_figure_semantics import MultimodalFigureSemanticExtractor
from paper_analysis.domain.execution import ExecutionPolicyRequest, ResolvedPolicy
from paper_analysis.domain.execution_context import execution_scope
from paper_analysis.domain.models import FigureMetadata
from paper_analysis.domain.qa import AnswerClaim, QuestionRequest
from paper_analysis.domain.schemas import ParsedDocument
from paper_analysis.runtime.budget import BudgetLedger


def completion_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, request=request, json={
        "id": "test", "object": "chat.completion", "created": 0,
        "model": "kimi-for-coding",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
    })


class ModelParameterControlsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = {
            "KIMI_MODEL": "kimi-for-coding", "KIMI_API_KEY": "text-fake",
            "KIMI_BASE_URL": "https://api.kimi.com/coding/v1",
            "VISION_MODEL": "qwen3.8-flash", "VISION_API_KEY": "vision-fake",
            "VISION_BASE_URL": "https://vision.invalid/v1",
        }

    def test_extraction_and_review_share_new_parameters_without_text_effort(self) -> None:
        with patch.dict(os.environ, {**self.env, "KIMI_REASONING_EFFORT": "low"}, clear=True):
            client = create_llm_client_from_env()
        ledger = BudgetLedger(job_id="vision-parameters", attempt=1, policy=ResolvedPolicy.resolve().effective)
        claim = AnswerClaim(claim_id="c1", statement="柱顶数值为 73。", basis="visual")
        payloads = [
            {"figure_type": "bar_chart", "direct_evidence": [claim.statement], "confidence": "高"},
            {"checks": [{"claim_id": "c1", "statement": claim.statement, "verdict": "supported",
                         "observation": "柱顶显示 73。", "rationale": "实际图像支持。"}]},
        ]
        responses = []
        for payload in payloads:
            response = Mock(status_code=200)
            response.json.return_value = {
                "choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 6, "total_tokens": 26},
            }
            responses.append(response)
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "pages" / "page_1.png"
            image.parent.mkdir()
            image.write_bytes(b"synthetic-image")
            figure = FigureMetadata(figure_id="Figure 1", page_number=1, page_snapshot_path=str(image))
            document = ParsedDocument(title="合成论文", raw_text="合成正文", figures=[figure])
            with execution_scope(ledger), patch(
                "paper_analysis.adapters.llm.openai_compatible.httpx.post", side_effect=responses,
            ) as post:
                batch = MultimodalFigureSemanticExtractor(vision_client=client).extract(
                    document=document, figures=[figure], execution_context=ledger,
                )
                checked = ImageClaimChecker(client).check(
                    request=QuestionRequest(question="图 1 数值是多少？", figure="1"),
                    claims=[claim], image_paths=[image], execution_context=ledger,
                )
        self.assertEqual(batch.artifacts[0].extraction_source, "multimodal_llm")
        self.assertEqual(checked.checks[0].verdict, "supported")
        self.assertEqual(post.call_count, 2)
        for call in post.call_args_list:
            payload = call.kwargs["json"]
            self.assertEqual(payload["model"], "qwen3.8-flash")
            self.assertEqual(payload["temperature"], 0.9)
            self.assertEqual(payload["max_tokens"], 16_384)
            self.assertNotIn("reasoning_effort", payload)
            self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer vision-fake")
        summary = ledger.summary()
        self.assertEqual(summary.call_count, 2)
        self.assertEqual(summary.actual_usage.total, 52)
        self.assertEqual([call.role for call in summary.calls], ["figure_observer", "visual_checker"])
        self.assertTrue(all(call.reservation >= 16_384 for call in summary.calls))

    def test_vision_output_limit_obeys_policy_and_explicit_call_override(self) -> None:
        with patch.dict(os.environ, self.env, clear=True):
            client = create_llm_client_from_env()
        policy = ResolvedPolicy.resolve(ExecutionPolicyRequest(max_output_tokens=1024)).effective
        ledger = BudgetLedger(job_id="clipped-vision", attempt=1, policy=policy)
        response = Mock(status_code=200)
        response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        with patch("paper_analysis.adapters.llm.openai_compatible.httpx.post", return_value=response) as post:
            client.complete_with_images(prompt="合成", image_paths=[], execution_context=ledger)
            client.complete_with_images(prompt="合成", image_paths=[], execution_context=ledger, max_output_tokens=512)
        self.assertEqual([call.kwargs["json"]["max_tokens"] for call in post.call_args_list], [1024, 512])
        self.assertEqual(ledger.summary().call_count, 2)

    def test_invalid_vision_output_limit_fails_before_any_request(self) -> None:
        for value in ("0", "-1", "63", "100001", "1.5", "nan", "", "oops"):
            with self.subTest(value=value), patch.dict(
                os.environ, {**self.env, "VISION_MAX_OUTPUT_TOKENS": value}, clear=True,
            ), patch("paper_analysis.adapters.llm.openai_compatible.httpx.post") as post:
                with self.assertRaisesRegex(ValueError, "VISION_MAX_OUTPUT_TOKENS"):
                    create_llm_client_from_env()
                post.assert_not_called()

    def test_output_limit_and_temperature_invalidate_visual_cache(self) -> None:
        configurations = [("4096", "0.2"), ("16384", "0.2"), ("16384", "0.9")]
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "page_1.png"
            image.write_bytes(b"same-image")
            figure = FigureMetadata(figure_id="Figure 1", caption="相同图注")
            keys = []
            for limit, temperature in configurations:
                with patch.dict(os.environ, {**self.env, "VISION_MAX_OUTPUT_TOKENS": limit,
                                             "VISION_TEMPERATURE": temperature}, clear=True):
                    client = create_llm_client_from_env()
                extractor = MultimodalFigureSemanticExtractor(vision_client=client)
                keys.append(extractor._cache_key(figure=figure, image_paths=[image]))
            self.assertEqual(len(set(keys)), 3)

    def test_kimi_effort_reaches_real_sdk_wire_for_both_text_roles(self) -> None:
        for effort in (None, "low", "high", "max", "none"):
            with self.subTest(effort=effort):
                env = self.env if effort is None else {**self.env, "KIMI_REASONING_EFFORT": effort}
                with patch.dict(os.environ, env, clear=True):
                    client = create_llm_client_from_env()
                ledger = BudgetLedger(job_id="text-effort", attempt=1, policy=ResolvedPolicy.resolve().effective)
                requests = []

                def send(request: httpx.Request) -> httpx.Response:
                    requests.append(json.loads(request.content))
                    return completion_response(request)

                with execution_scope(ledger), patch("httpx.HTTPTransport.handle_request", side_effect=send):
                    for role in ("question_answer", "fact_checker"):
                        self.assertEqual(client.for_role(role).call("合成输入"), "ok")
                self.assertEqual(len(requests), 2)
                for body in requests:
                    self.assertEqual(body["model"], "kimi-for-coding")
                    self.assertEqual(body["max_tokens"], 65_536)
                    self.assertFalse(body["stream"])
                    if effort is None:
                        self.assertNotIn("reasoning_effort", body)
                    else:
                        self.assertEqual(body["reasoning_effort"], effort)
                    self.assertNotIn("extra_body", body)
                self.assertEqual(ledger.summary().actual_usage.total, 24)
                self.assertEqual(client.audit_metadata()["reasoning_effort"], effort)

    def test_kimi_effort_reaches_async_sdk_wire(self) -> None:
        with patch.dict(os.environ, {**self.env, "KIMI_REASONING_EFFORT": "low"}, clear=True):
            client = create_llm_client_from_env()
        ledger = BudgetLedger(job_id="async-effort", attempt=1, policy=ResolvedPolicy.resolve().effective)
        requests = []

        async def send(request: httpx.Request) -> httpx.Response:
            requests.append(json.loads(request.content))
            return completion_response(request)

        with execution_scope(ledger):
            llm = client.to_crewai_llm()
        with patch("httpx.AsyncHTTPTransport.handle_async_request", side_effect=send):
            self.assertEqual(asyncio.run(llm.acall("合成输入")), "ok")
        self.assertEqual(requests[0]["reasoning_effort"], "low")
        self.assertEqual(ledger.summary().actual_usage.total, 12)

    def test_invalid_kimi_effort_is_rejected_instead_of_silent_default(self) -> None:
        for value in ("medium", "xhigh", "off", "invalid"):
            with self.subTest(value=value), patch.dict(
                os.environ, {**self.env, "KIMI_REASONING_EFFORT": value}, clear=True,
            ):
                with self.assertRaisesRegex(ValueError, "KIMI_REASONING_EFFORT"):
                    create_llm_client_from_env()


if __name__ == "__main__":
    unittest.main()
