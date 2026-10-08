from __future__ import annotations

import base64
import hashlib
from typing import TYPE_CHECKING, Any
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from crewai import LLM

from paper_analysis.adapters.llm.base import LLMClient
from paper_analysis.domain.execution_context import current_execution
from paper_analysis.domain.execution import ResolvedPolicy
from paper_analysis.domain.execution import CallStatus, CapabilityStatus, ModelCapabilities, TokenUsage

if TYPE_CHECKING:
    from paper_analysis.runtime.budget import BudgetLedger, Reservation

_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class VisionNotConfiguredError(RuntimeError):
    """Raised when vision completion is requested without a configured vision model."""


class OpenAICompatibleLLM(LLMClient):
    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        provider: str = "openai",
        temperature: float = 0.2,
        vision_model: str | None = None,
        request_timeout: float = 120.0,
        vision_api_key: str | None = None,
        vision_base_url: str | None = None,
        vision_temperature: float | None = None,
        max_retries: int = 0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._provider = provider
        self._temperature = temperature
        self._vision_model = vision_model
        self._request_timeout = request_timeout
        self._vision_api_key = api_key if vision_api_key is None else vision_api_key
        self._vision_base_url = base_url if vision_base_url is None else vision_base_url
        self._vision_temperature = temperature if vision_temperature is None else vision_temperature
        self._max_retries = max(0, min(max_retries, 3))

    @property
    def vision_model(self) -> str | None:
        return self._vision_model

    def audit_metadata(self) -> dict[str, str | None]:
        return {"model": self._model, "vision_model": self._vision_model,
                "vision_configuration_fingerprint": self.vision_cache_identity() if self._vision_model else None}

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            provider=self._provider,
            model=self._model,
            endpoint_id=self._endpoint_id(self._base_url),
            text=CapabilityStatus.VERIFIED,
            image=CapabilityStatus.UNVERIFIED if self._vision_model else CapabilityStatus.UNSUPPORTED,
            structured_output=CapabilityStatus.UNVERIFIED,
            usage=CapabilityStatus.UNVERIFIED,
            native_reasoning_effort=CapabilityStatus.UNSUPPORTED,
            output_token_limits=CapabilityStatus.UNVERIFIED,
            timeout=CapabilityStatus.VERIFIED,
            notes=["能力状态来自配置与适配器协议，未替代具体模型端点冒烟。"],
        )

    def vision_cache_identity(self) -> str:
        """区分端点、模型与采样配置；不把密钥纳入缓存或审计。"""
        config = (self._vision_base_url or "").rstrip('/') + "\n" + (self._vision_model or "")
        return hashlib.sha256(f"{config}\n{self._vision_temperature}".encode()).hexdigest()

    def for_role(self, role: str) -> LLM:
        return self.to_crewai_llm(role=role)

    def to_crewai_llm(self, *, role: str = "text") -> LLM:
        from paper_analysis.adapters.llm.metering import RequestMeter
        from paper_analysis.runtime.budget import BudgetLedger
        ledger = current_execution() or BudgetLedger(job_id="standalone", attempt=1,
            policy=ResolvedPolicy.resolve().effective)
        llm = LLM(
            model=self._model,
            api_key=self._api_key,
            base_url=self._base_url,
            provider=self._provider,
            temperature=self._temperature,
            max_tokens=ledger.policy.max_output_tokens,
            timeout=min(self._request_timeout, ledger.remaining_seconds()),
            max_retries=0,
        )
        meter = RequestMeter(ledger, self._model, self._endpoint_id(self._base_url), role=role)
        # 使用 SDK 的 client 配置保留 CrewAI 的原生工具与结构化输出能力。
        llm._client = llm._client.with_options(http_client=httpx.Client(
            event_hooks={"request": [meter.request], "response": [meter.response]}), max_retries=0)
        llm._async_client = llm._async_client.with_options(http_client=httpx.AsyncClient(
            event_hooks={"request": [meter.arequest], "response": [meter.aresponse]}), max_retries=0)
        return llm

    def complete_with_images(
        self,
        *,
        prompt: str,
        image_paths: list[Path],
        execution_context: "BudgetLedger | None" = None,
        stage: str = "vision",
        role: str = "image_observer",
        max_output_tokens: int | None = None,
    ) -> str:
        if not self._vision_model:
            raise VisionNotConfiguredError(
                "未配置视觉模型。请设置 KIMI_VISION_MODEL（或 OPENAI_VISION_MODEL）后重试。"
            )
        if not self._vision_base_url:
            raise VisionNotConfiguredError("视觉调用需要 base_url。")

        execution_context = execution_context or current_execution()
        max_output_tokens = min(max_output_tokens or 4096, execution_context.policy.max_output_tokens) if execution_context else (max_output_tokens or 4096)
        content: list[dict] = [{"type": "text", "text": prompt}]
        for image_path in image_paths:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self._to_data_uri(image_path)},
                }
            )

        payload = {
            "model": self._vision_model,
            "messages": [{"role": "user", "content": content}],
            "temperature": self._vision_temperature,
        }
        if max_output_tokens is not None:
            payload["max_tokens"] = max_output_tokens
        headers = {"Content-Type": "application/json"}
        if self._vision_api_key:
            headers["Authorization"] = f"Bearer {self._vision_api_key}"

        endpoint = f"{self._vision_base_url.rstrip('/')}/chat/completions"
        endpoint_id = self._endpoint_id(self._vision_base_url)
        attempts = self._max_retries + 1
        for index in range(attempts):
            reservation = None
            data: Any = None
            response: Any = None
            if execution_context is not None:
                from paper_analysis.runtime.budget import estimate_image_tokens, estimate_text_tokens

                reservation = execution_context.reserve(
                    input_tokens=estimate_text_tokens(prompt),
                    image_tokens=estimate_image_tokens(len(image_paths)),
                    max_output_tokens=max_output_tokens,
                    stage=stage,
                    role=role,
                    model=self._vision_model,
                    endpoint_id=endpoint_id,
                )
            try:
                if execution_context is not None and reservation is not None:
                    execution_context.mark_sent(reservation)
                response = httpx.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=min(self._request_timeout, execution_context.remaining_seconds()) if execution_context else self._request_timeout,
                )
                if isinstance(response.status_code, int) and (response.status_code >= 500 or response.status_code == 429):
                    response.raise_for_status()
                    raise RuntimeError(f"视觉供应商返回 HTTP {response.status_code}。")
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("视觉供应商返回空内容。")
                if execution_context is not None and reservation is not None:
                    execution_context.settle(
                        reservation,
                        usage=_token_usage(data.get("usage")),
                    )
                return content
            except (httpx.TimeoutException, httpx.TransportError):
                if execution_context is not None and reservation is not None:
                    execution_context.settle(reservation, usage=None, status=CallStatus.TIMEOUT)
                if index + 1 < attempts:
                    if execution_context is not None:
                        execution_context.mark_retry()
                    continue
                raise
            except Exception:
                if execution_context is not None and reservation is not None:
                    execution_context.settle(
                        reservation,
                        usage=_token_usage(data.get("usage") if isinstance(data, dict) else None),
                        status=CallStatus.PROVIDER_ERROR,
                    )
                if index + 1 < attempts and _retryable_response(response):
                    if execution_context is not None:
                        execution_context.mark_retry()
                    continue
                raise

        raise RuntimeError("视觉请求未执行。")

    @staticmethod
    def _to_data_uri(image_path: Path) -> str:
        mime = _MIME_BY_SUFFIX.get(image_path.suffix.lower(), "image/png")
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    @staticmethod
    def _endpoint_id(base_url: str | None) -> str:
        if not base_url:
            return "unknown"
        parsed = urlsplit(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def _retryable_response(response: Any) -> bool:
    status = getattr(response, "status_code", None)
    return status == 429 or isinstance(status, int) and status >= 500


def _token_usage(payload: Any) -> TokenUsage | None:
    if not isinstance(payload, dict):
        return None
    input_tokens = payload.get("prompt_tokens", payload.get("input_tokens"))
    output_tokens = payload.get("completion_tokens", payload.get("output_tokens"))
    total_tokens = payload.get("total_tokens")
    cached = payload.get("prompt_tokens_details", {}).get("cached_tokens") if isinstance(
        payload.get("prompt_tokens_details"), dict
    ) else None
    reasoning = payload.get("completion_tokens_details", {}).get("reasoning_tokens") if isinstance(
        payload.get("completion_tokens_details"), dict
    ) else None
    values = {"input": input_tokens, "output": output_tokens, "total": total_tokens,
              "cached": cached, "reasoning": reasoning}
    if not any(value is not None for value in values.values()):
        return None
    return TokenUsage(**{key: int(value) if value is not None else None for key, value in values.items()})
