import os

from paper_analysis.adapters.llm.base import LLMClient
from paper_analysis.adapters.llm.openai_compatible import OpenAICompatibleLLM

KIMI_DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
KIMI_DEFAULT_MODEL = "kimi-k3"


def create_llm_client(
    *,
    provider: str,
    model: str,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.2,
    vision_model: str | None = None,
) -> LLMClient:
    if provider in {"default", "openai_compatible", "kimi"}:
        return OpenAICompatibleLLM(
            api_key=api_key,
            base_url=base_url,
            model=model,
            provider="openai",
            temperature=temperature,
            vision_model=vision_model,
        )

    raise ValueError(f"Unsupported llm provider: {provider}")


def create_llm_client_from_env() -> LLMClient | None:
    kimi_vars = {
        "model": os.getenv("KIMI_MODEL"),
        "api_key": os.getenv("KIMI_API_KEY"),
        "base_url": os.getenv("KIMI_BASE_URL"),
        "temperature": os.getenv("KIMI_TEMPERATURE"),
        "vision_model": os.getenv("KIMI_VISION_MODEL"),
    }
    if any(kimi_vars.values()):
        if not kimi_vars["api_key"]:
            raise ValueError(
                "后端启动失败：缺少 KIMI_API_KEY。"
                "请在项目根目录 .env 或当前 shell 环境中设置 KIMI_API_KEY 后重新启动。"
            )
        return OpenAICompatibleLLM(
            model=kimi_vars["model"] or KIMI_DEFAULT_MODEL,
            api_key=kimi_vars["api_key"],
            base_url=kimi_vars["base_url"] or KIMI_DEFAULT_BASE_URL,
            provider="openai",
            temperature=float(kimi_vars["temperature"] or "0.2"),
            vision_model=kimi_vars["vision_model"],
        )

    model = os.getenv("OPENAI_MODEL") or os.getenv("MODEL")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    provider = os.getenv("OPENAI_PROVIDER")
    temperature = os.getenv("OPENAI_TEMPERATURE")
    vision_model = os.getenv("OPENAI_VISION_MODEL")

    if not any([model, api_key, base_url, provider, temperature, vision_model]):
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
        vision_model=vision_model,
    )
