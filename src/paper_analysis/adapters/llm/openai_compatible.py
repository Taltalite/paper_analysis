from __future__ import annotations

import base64
from pathlib import Path

import httpx
from crewai import LLM

from paper_analysis.adapters.llm.base import LLMClient

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
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._provider = provider
        self._temperature = temperature
        self._vision_model = vision_model
        self._request_timeout = request_timeout

    @property
    def vision_model(self) -> str | None:
        return self._vision_model

    def to_crewai_llm(self) -> LLM:
        return LLM(
            model=self._model,
            api_key=self._api_key,
            base_url=self._base_url,
            provider=self._provider,
            temperature=self._temperature,
        )

    def complete_with_images(self, *, prompt: str, image_paths: list[Path]) -> str:
        if not self._vision_model:
            raise VisionNotConfiguredError(
                "未配置视觉模型。请设置 KIMI_VISION_MODEL（或 OPENAI_VISION_MODEL）后重试。"
            )
        if not self._base_url:
            raise VisionNotConfiguredError("视觉调用需要 base_url。")

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
            "temperature": self._temperature,
        }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        endpoint = f"{self._base_url.rstrip('/')}/chat/completions"
        response = httpx.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=self._request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _to_data_uri(image_path: Path) -> str:
        mime = _MIME_BY_SUFFIX.get(image_path.suffix.lower(), "image/png")
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
