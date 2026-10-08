import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from paper_analysis.adapters.llm.openai_compatible import OpenAICompatibleLLM
from paper_analysis.domain.execution import ExecutionPolicyRequest, ResolvedPolicy, TokenUsage
from paper_analysis.domain.execution_context import execution_scope
from paper_analysis.runtime.budget import BudgetLedger


class PlanBudgetTests(unittest.TestCase):
    def test_actual_http_tool_rounds_cannot_exceed_budget(self):
        calls = []
        policy = ResolvedPolicy.resolve(ExecutionPolicyRequest(max_calls=1, max_output_tokens=64)).effective
        ledger = BudgetLedger(job_id="j", attempt=1, policy=policy)
        with execution_scope(ledger):
            llm = OpenAICompatibleLLM(model="fake", api_key="fake", base_url="https://fake.invalid/v1").to_crewai_llm()
        def send(request):
            calls.append(json.loads(request.content))
            return httpx.Response(200, request=request, json={"id":"test", "object":"chat.completion",
                "created":0, "model":"fake", "choices":[{"index":0,"message":{"role":"assistant","content":"ok"},"finish_reason":"stop"}],
                "usage":{"prompt_tokens":10,"completion_tokens":2,"total_tokens":12}})
        with patch("httpx.HTTPTransport.handle_request", side_effect=send):
            self.assertEqual(llm.call("first"), "ok")
            with self.assertRaises(Exception):
                llm.call("second")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["max_tokens"], 64)
        self.assertEqual(ledger.summary().actual_usage.total, 12)
        self.assertEqual(ledger.summary().call_count, 1)

    def test_async_transport_records_usage(self):
        ledger = BudgetLedger(job_id="j", attempt=1, policy=ResolvedPolicy.resolve().effective)
        with execution_scope(ledger):
            llm = OpenAICompatibleLLM(model="fake", api_key="fake", base_url="https://fake.invalid/v1").to_crewai_llm()
        async def send(request):
            return httpx.Response(200, request=request, json={"id":"test","object":"chat.completion","created":0,"model":"fake",
                "choices":[{"index":0,"message":{"role":"assistant","content":"ok"},"finish_reason":"stop"}],
                "usage":{"prompt_tokens":10,"completion_tokens":2,"total_tokens":12}})
        with patch("httpx.AsyncHTTPTransport.handle_async_request", side_effect=send):
            self.assertEqual(asyncio.run(llm.acall("first")), "ok")
        self.assertEqual(ledger.summary().actual_usage.total, 12)

    def test_partial_usage_retry_persistence_and_idempotency(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "budget.json"
            policy = ResolvedPolicy.resolve(ExecutionPolicyRequest(max_calls=1)).effective
            ledger = BudgetLedger(job_id="j", attempt=1, policy=policy, path=path)
            reservation = ledger.reserve(input_tokens=10, stage="t", role="t", model="m", endpoint_id="e")
            ledger.mark_sent(reservation)
            ledger.settle(reservation, usage=TokenUsage(input=50))
            charge = ledger.settled_charge
            ledger.settle(reservation, usage=TokenUsage(input=50))
            self.assertEqual(ledger.settled_charge, charge)
            self.assertEqual(ledger.summary().calls[0].usage.input, 50)
            restored = BudgetLedger(job_id="j", attempt=2, policy=policy, path=path)
            self.assertEqual(restored.settled_charge, charge)
            with self.assertRaises(Exception):
                restored.reserve(input_tokens=10, stage="t", role="t", model="m", endpoint_id="e")
