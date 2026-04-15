from __future__ import annotations

from crewai import LLM

from paper_analysis.adapters.llm.base import LLMClient


class OpenAICompatibleLLM(LLMClient):
    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        provider: str = "openai",
        temperature: float = 0.2,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._provider = provider
        self._temperature = temperature

    def to_crewai_llm(self) -> LLM:
        return LLM(
            model=self._model,
            api_key=self._api_key,
            base_url=self._base_url,
            provider=self._provider,
            temperature=self._temperature,
        )
