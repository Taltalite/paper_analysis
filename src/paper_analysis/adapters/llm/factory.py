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
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    provider = os.getenv("OPENAI_PROVIDER")
    temperature = os.getenv("OPENAI_TEMPERATURE")

    if not any([model, api_key, base_url, provider, temperature]):
        return None

    if not model:
        raise ValueError(
            "后端启动失败：缺少 OPENAI_MODEL。"
            "请在项目根目录 .env 或当前 shell 环境中设置 OPENAI_MODEL 后重新启动。"
        )

    if not api_key:
        raise ValueError(
            "后端启动失败：缺少 OPENAI_API_KEY。"
            "请在项目根目录 .env 或当前 shell 环境中设置 OPENAI_API_KEY 后重新启动。"
        )

    return OpenAICompatibleLLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
        provider=provider or "openai",
        temperature=float(temperature or "0.2"),
    )
