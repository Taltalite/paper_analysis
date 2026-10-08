from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from paper_analysis.domain.execution import ModelCapabilities

if TYPE_CHECKING:
    from paper_analysis.runtime.budget import BudgetLedger


class LLMClient(ABC):
    def audit_metadata(self) -> dict[str, str | None]:
        return {"model": type(self).__name__, "vision_model": None}

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            provider="unknown",
            model=type(self).__name__,
            endpoint_id="unknown",
        )

    def for_role(self, role: str) -> Any:
        return self.to_crewai_llm()

    @abstractmethod
    def to_crewai_llm(self) -> Any:
        raise NotImplementedError


@runtime_checkable
class VisionLLMClient(Protocol):
    """Optional vision capability for LLM clients that accept image inputs."""

    @property
    def vision_model(self) -> str | None:
        ...

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
        ...
