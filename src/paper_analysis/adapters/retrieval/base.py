from __future__ import annotations

from typing import Protocol


class RetrievalAdapter(Protocol):
    """外部检索扩展点（如论文库、DOI 数据源）。

    默认服务不装配任何 retrieval adapter；外部事实检查能力
    仅应通过注入该接口接入，不与核心服务硬耦合。
    """

    def retrieve(self, *, query: str, max_results: int = 5) -> list[str]:
        ...
