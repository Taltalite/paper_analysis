from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


class LLMClient(ABC):
    def audit_metadata(self) -> dict[str, str | None]:
        return {"model": type(self).__name__, "vision_model": None}

    @abstractmethod
    def to_crewai_llm(self) -> Any:
        raise NotImplementedError


@runtime_checkable
class VisionLLMClient(Protocol):
    """Optional vision capability for LLM clients that accept image inputs."""

    @property
    def vision_model(self) -> str | None:
        ...

    def complete_with_images(self, *, prompt: str, image_paths: list[Path]) -> str:
        ...
