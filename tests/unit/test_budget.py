import unittest

from paper_analysis.domain.execution import CallStatus, ExecutionPolicy, StopReason, TokenUsage
from paper_analysis.runtime.budget import BudgetExceededError, BudgetLedger


def policy(**overrides) -> ExecutionPolicy:
    values = {
        "token_budget": 1_000,
        "max_calls": 3,
        "max_output_tokens": 100,
        "timeout_seconds": 60.0,
        "max_followups": 2,
        "max_figures": 2,
        "max_visual_reviews": 1,
    }
    values.update(overrides)
    return ExecutionPolicy(**values)


class BudgetLedgerTests(unittest.TestCase):
    def test_reservation_is_atomic_and_rejects_over_budget_call(self) -> None:
        ledger = BudgetLedger(job_id="job", attempt=1, policy=policy(token_budget=300))
        first = ledger.reserve(
            input_tokens=100,
            max_output_tokens=100,
            stage="draft",
            role="text",
            model="fake",
            endpoint_id="fake:text",
        )
        self.assertEqual(ledger.available_tokens, 100)
        with self.assertRaises(BudgetExceededError) as context:
            ledger.reserve(
                input_tokens=1,
                max_output_tokens=100,
                stage="check",
                role="checker",
                model="fake",
                endpoint_id="fake:text",
            )
        self.assertEqual(context.exception.reason, StopReason.TOKEN_BUDGET_EXHAUSTED)
        ledger.release_not_sent(first)
        self.assertEqual(ledger.settled_charge, 0)

    def test_provider_usage_and_unknown_usage_are_not_written_as_zero(self) -> None:
        ledger = BudgetLedger(job_id="job", attempt=1, policy=policy())
        provider = ledger.reserve(
            input_tokens=10,
            max_output_tokens=100,
            stage="draft",
            role="text",
            model="fake",
            endpoint_id="fake:text",
        )
        ledger.mark_sent(provider)
        ledger.settle(provider, usage=TokenUsage(input=12, output=8, total=20))
        unknown = ledger.reserve(
            input_tokens=10,
            max_output_tokens=100,
            stage="check",
            role="checker",
            model="fake",
            endpoint_id="fake:text",
        )
        ledger.mark_sent(unknown)
        ledger.settle(unknown, usage=None, status=CallStatus.TIMEOUT)
        summary = ledger.summary(stop_reason=StopReason.PROVIDER_ERROR)
        self.assertEqual(summary.actual_usage.total, 20)
        self.assertTrue(summary.unknown_usage)
        self.assertGreater(summary.estimated_usage.total or 0, 0)
        self.assertEqual(summary.stop_reason, StopReason.PROVIDER_ERROR)

    def test_cache_hit_has_no_token_charge(self) -> None:
        ledger = BudgetLedger(job_id="job", attempt=1, policy=policy(token_budget=256))
        ledger.record_cache_hit(stage="vision", role="observer", model="fake", endpoint_id="fake:image")
        summary = ledger.summary()
        self.assertEqual(summary.cache_hits, 1)
        self.assertEqual(summary.call_count, 0)
        self.assertEqual(ledger.settled_charge, 0)


if __name__ == "__main__":
    unittest.main()
