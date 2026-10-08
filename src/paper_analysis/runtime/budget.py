"""与供应商无关的请求前预留和请求后结算账本。"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4
from pathlib import Path
from paper_analysis.adapters.storage.qa_store import atomic_json

from paper_analysis.domain.execution import (
    CallRecord,
    CallStatus,
    ExecutionPolicy,
    ExecutionSummary,
    StopReason,
    TokenUsage,
    UsageSource,
)


class BudgetExceededError(RuntimeError):
    def __init__(self, reason: StopReason, *, requested: int, available: int) -> None:
        self.reason = reason
        self.requested = requested
        self.available = available
        super().__init__(
            f"执行预算不足：{reason.value}（需要 {requested}，可用 {available}）。"
        )


class DeadlineExceededError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("执行已超过策略 timeout_seconds。")
        self.reason = StopReason.DEADLINE_EXCEEDED


@dataclass(frozen=True)
class Reservation:
    call_id: str
    amount: int


def estimate_text_tokens(text: str) -> int:
    """没有供应商 tokenizer 时使用的可解释保守估算。

    CJK 字符按单字符计，ASCII 连续片段按约 4 字符一个 token，JSON 标点
    和空白保留少量开销。该值只用于预留，不冒充供应商账单。
    """

    if not text:
        return 0
    cjk = sum(1 for char in text if "\u3400" <= char <= "\u9fff")
    non_cjk = len(text) - cjk
    return max(1, cjk + (non_cjk + 3) // 4 + min(256, text.count("{") + text.count("[")))


def estimate_image_tokens(image_count: int) -> int:
    """按图像数量保守预留，不使用 base64 长度推断图像 token。"""

    return max(0, image_count) * 1_024


class BudgetLedger:
    """单个 job/attempt 的线程安全账本。

    账本不持有全局状态。并行阶段必须共享同一个实例，才能让 outstanding
    reservation 在请求前原子扣除。
    """

    def __init__(self, *, job_id: str, attempt: int, policy: ExecutionPolicy, path: Path | None = None) -> None:
        self.job_id = job_id
        self.attempt = attempt
        self.policy = policy
        self.started_monotonic = time.monotonic()
        self._lock = threading.RLock()
        self._records: dict[str, CallRecord] = {}
        self._outstanding: dict[str, int] = {}
        self._settled_charge = 0
        self._cache_hits = 0
        self._retries = 0
        self.path = path
        self.stop_reason = None
        self.verification_reserve = 0
        if path and path.exists():
            previous = ExecutionSummary.model_validate_json(path.read_text())
            self._records = {r.call_id: r for r in previous.calls}
            self._cache_hits = previous.cache_hits
            self._retries = previous.retry_count
            for record in self._records.values():
                if record.status in {CallStatus.RESERVED, CallStatus.SENT}:
                    record.status = CallStatus.TIMEOUT
                    record.usage_source = UsageSource.UNKNOWN
                    record.usage = TokenUsage(reserved=record.reservation, unknown=True)
                if record.status not in {CallStatus.CACHE_HIT, CallStatus.NOT_SENT}:
                    self._settled_charge += (record.usage.total if record.usage and record.usage.total is not None else record.reservation)

    def _persist(self) -> None:
        if self.path:
            atomic_json(self.path, self.summary(stop_reason=self.stop_reason or "running"))

    def remaining_seconds(self) -> float:
        self.ensure_deadline()
        return max(0.01, self.policy.timeout_seconds - (time.monotonic() - self.started_monotonic))

    @property
    def settled_charge(self) -> int:
        with self._lock:
            return self._settled_charge

    @property
    def outstanding_reservations(self) -> int:
        with self._lock:
            return sum(self._outstanding.values())

    @property
    def available_tokens(self) -> int:
        with self._lock:
            return self.policy.token_budget - self._settled_charge - sum(self._outstanding.values())

    def ensure_deadline(self) -> None:
        if time.monotonic() - self.started_monotonic > self.policy.timeout_seconds:
            self.stop_reason = StopReason.DEADLINE_EXCEEDED
            raise DeadlineExceededError()

    def reserve(
        self,
        *,
        input_tokens: int,
        image_tokens: int = 0,
        max_output_tokens: int | None = None,
        stage: str,
        role: str,
        model: str,
        endpoint_id: str,
    ) -> Reservation:
        self.ensure_deadline()
        amount = max(0, input_tokens) + max(0, image_tokens) + max(
            0, max_output_tokens if max_output_tokens is not None else self.policy.max_output_tokens
        )
        with self._lock:
            if self.stop_reason in {StopReason.TOKEN_BUDGET_EXHAUSTED, StopReason.CALL_BUDGET_EXHAUSTED}:
                raise BudgetExceededError(self.stop_reason, requested=amount, available=max(0, self.available_tokens))
            sent_calls = sum(r.status not in {CallStatus.CACHE_HIT, CallStatus.NOT_SENT} for r in self._records.values())
            if sent_calls >= self.policy.max_calls:
                self.stop_reason = StopReason.CALL_BUDGET_EXHAUSTED
                self._persist()
                raise BudgetExceededError(
                    StopReason.CALL_BUDGET_EXHAUSTED,
                    requested=amount,
                    available=max(0, self.available_tokens),
                )
            available = self.available_tokens
            if role not in {"fact_checker", "visual_checker"}:
                available -= self.verification_reserve
            if amount > available:
                self.stop_reason = StopReason.TOKEN_BUDGET_EXHAUSTED
                self._persist()
                raise BudgetExceededError(
                    StopReason.TOKEN_BUDGET_EXHAUSTED,
                    requested=amount,
                    available=max(0, available),
                )
            call_id = uuid4().hex
            self._outstanding[call_id] = amount
            self._records[call_id] = CallRecord(
                call_id=call_id,
                job_id=self.job_id,
                attempt=self.attempt,
                stage=stage,
                role=role,
                model=model,
                endpoint_id=endpoint_id,
                status=CallStatus.RESERVED,
                usage_source=UsageSource.ESTIMATED,
                reservation=amount,
            )
            self._persist()
            return Reservation(call_id=call_id, amount=amount)

    def mark_sent(self, reservation: Reservation | None) -> None:
        if reservation is None:
            return
        with self._lock:
            record = self._records[reservation.call_id]
            record.status = CallStatus.SENT
            self._persist()

    def settle(
        self,
        reservation: Reservation | None,
        *,
        usage: TokenUsage | None,
        status: CallStatus = CallStatus.SUCCEEDED,
    ) -> None:
        if reservation is None:
            return
        with self._lock:
            if reservation.call_id not in self._outstanding:
                return
            reserved = self._outstanding.pop(reservation.call_id)
            record = self._records[reservation.call_id]
            record.ended_at = datetime.now(UTC)
            record.status = status
            if usage is None:
                # 已发送但没有回执：保留未知状态，并保守扣留预留额，不能写成 0。
                record.usage = TokenUsage(reserved=reserved, unknown=True)
                record.usage_source = UsageSource.UNKNOWN
                self._settled_charge += reserved
                self._persist()
                return
            total = usage.total
            if total is None and usage.input is not None and usage.output is not None:
                total = usage.input + usage.output
                usage = usage.model_copy(update={"total": total})
            if total is None:
                usage = usage.model_copy(update={"reserved": reserved, "unknown": True})
                record.usage = usage
                record.usage_source = UsageSource.UNKNOWN
                self._settled_charge += reserved
            else:
                record.usage_source = UsageSource.PROVIDER
                record.usage = usage
                self._settled_charge += total
            self._persist()

    def release_not_sent(self, reservation: Reservation) -> None:
        if reservation is None:
            return
        with self._lock:
            if reservation.call_id not in self._outstanding:
                return
            reserved = self._outstanding.pop(reservation.call_id)
            record = self._records[reservation.call_id]
            record.ended_at = datetime.now(UTC)
            record.status = CallStatus.NOT_SENT
            record.usage_source = UsageSource.NOT_SENT
            record.usage = TokenUsage(reserved=reserved)
            self._persist()

    def record_cache_hit(
        self,
        *,
        stage: str,
        role: str,
        model: str,
        endpoint_id: str,
    ) -> None:
        with self._lock:
            self._cache_hits += 1
            call_id = uuid4().hex
            self._records[call_id] = CallRecord(
                call_id=call_id,
                job_id=self.job_id,
                attempt=self.attempt,
                stage=stage,
                role=role,
                model=model,
                endpoint_id=endpoint_id,
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
                status=CallStatus.CACHE_HIT,
                usage_source=UsageSource.CACHE,
                reservation=0,
            )

            self._persist()

    def mark_retry(self) -> None:
        with self._lock:
            self._retries += 1
            self._persist()

    def summary(self, *, stop_reason: StopReason | str = StopReason.COMPLETED) -> ExecutionSummary:
        with self._lock:
            records = [r.model_copy(deep=True) for r in self._records.values()]
            provider = [
                item.usage for item in records
                if item.usage is not None and item.usage_source == UsageSource.PROVIDER
            ]
            estimated = [
                item for item in records
                if item.usage_source in {UsageSource.ESTIMATED, UsageSource.UNKNOWN}
            ]
            actual_input = _sum_known(item.input for item in provider)
            actual_output = _sum_known(item.output for item in provider)
            actual_total = _sum_known(item.total for item in provider)
            estimated_total = sum(item.reservation for item in estimated)
            unknown = any(item.usage_source == UsageSource.UNKNOWN or item.status in {CallStatus.SENT, CallStatus.RESERVED} for item in records)
            return ExecutionSummary(
                actual_usage=TokenUsage(input=actual_input, output=actual_output, total=actual_total, cached=_sum_known(item.cached for item in provider), reasoning=_sum_known(item.reasoning for item in provider)),
                estimated_usage=TokenUsage(total=estimated_total, estimated=True) if estimated_total else TokenUsage(),
                unknown_usage=unknown,
                call_count=sum(item.status not in {CallStatus.CACHE_HIT, CallStatus.NOT_SENT} for item in records),
                retry_count=self._retries,
                cache_hits=self._cache_hits,
                budget=self.policy,
                elapsed_seconds=round(max(0.0, time.monotonic() - self.started_monotonic), 3),
                stop_reason=stop_reason,
                calls=records,
            )


def _sum_known(values):  # noqa: ANN001
    values = [value for value in values if value is not None]
    return sum(values) if values else None



def seal_interrupted_budget(path: Path, reason: str) -> None:
    if not path.exists():
        return
    previous = ExecutionSummary.model_validate_json(path.read_text())
    if previous.budget is None:
        return
    records = previous.calls
    ledger = BudgetLedger(job_id=records[-1].job_id if records else "interrupted",
        attempt=records[-1].attempt if records else 1, policy=previous.budget, path=path)
    summary = ledger.summary(stop_reason=reason)
    summary.elapsed_seconds = previous.elapsed_seconds
    atomic_json(path, summary)
