"""HTTP hooks 覆盖 CrewAI SDK 工具/格式修复的每一次请求。"""
from __future__ import annotations

import json
from typing import Any

import httpx

from paper_analysis.domain.execution import CallStatus, TokenUsage


class RequestMeter:
    def __init__(self, ledger: Any, model: str, endpoint: str, role: str = "text") -> None:
        self.ledger, self.model, self.endpoint, self.role = ledger, model, endpoint, role

    def request(self, request: httpx.Request) -> None:
        from paper_analysis.runtime.budget import estimate_text_tokens
        body = json.loads(request.content)
        # 记录完整实际消息/工具/schema 的估算，绝不保存原 prompt 或凭据。
        body["max_tokens"] = self.ledger.policy.max_output_tokens
        body.pop("max_completion_tokens", None)
        body["stream"] = False
        content = json.dumps(body, ensure_ascii=False).encode()
        # httpx 没有公开可写 content；使用新 ByteStream 并更新已读取内容。
        request.stream = httpx.ByteStream(content)
        request._content = content
        request.headers["content-length"] = str(len(content))
        limit = self.ledger.remaining_seconds()
        request.extensions["timeout"] = {k: min(limit, 120.0) for k in ("connect", "read", "write", "pool")}
        reservation = self.ledger.reserve(input_tokens=estimate_text_tokens(content.decode()),
            stage="text_http", role=self.role, model=self.model, endpoint_id=self.endpoint)
        request.extensions["paper_reservation"] = reservation
        self.ledger.mark_sent(reservation)

    def response(self, response: httpx.Response) -> None:
        response.read()
        self._settle(response)

    async def arequest(self, request: httpx.Request) -> None:
        self.request(request)

    async def aresponse(self, response: httpx.Response) -> None:
        await response.aread()
        self._settle(response)

    def _settle(self, response: httpx.Response) -> None:
        usage = None
        try:
            raw = response.json().get("usage")
            if isinstance(raw, dict):
                usage = TokenUsage(input=raw.get("prompt_tokens"), output=raw.get("completion_tokens"),
                    total=raw.get("total_tokens"), cached=(raw.get("prompt_tokens_details") or {}).get("cached_tokens"),
                    reasoning=(raw.get("completion_tokens_details") or {}).get("reasoning_tokens"))
        except (ValueError, AttributeError, TypeError):
            pass
        self.ledger.settle(response.request.extensions["paper_reservation"], usage=usage,
            status=CallStatus.SUCCEEDED if response.is_success else CallStatus.PROVIDER_ERROR)
