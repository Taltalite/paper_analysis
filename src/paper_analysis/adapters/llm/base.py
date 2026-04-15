from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

class LLMClient(ABC):
    @abstractmethod
    def to_crewai_llm(self) -> Any:
        raise NotImplementedError
