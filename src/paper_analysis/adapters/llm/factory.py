import os

from paper_analysis.adapters.llm.base import LLMClient
from paper_analysis.adapters.llm.openai_compatible import OpenAICompatibleLLM


def create_llm_client(
    *,
    provider: str,
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.2,
) -> LLMClient:
    if provider in {"default", "openai_compatible"}:
        return OpenAICompatibleLLM(
            api_key=api_key,
            base_url=base_url,
            model=model,
            provider="openai",
            temperature=temperature,
        )

    raise ValueError(f"Unsupported llm provider: {provider}")


def create_llm_client_from_env() -> LLMClient | None:
    model = os.getenv("OPENAI_MODEL") or os.getenv("MODEL")
    if not model:
        return None

    return OpenAICompatibleLLM(
        model=model,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        provider=os.getenv("OPENAI_PROVIDER", "openai"),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
    )
