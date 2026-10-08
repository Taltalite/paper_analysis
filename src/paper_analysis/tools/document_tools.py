"""文档由后端绑定，模型只能提交检索参数，不能替换原文或回传全文。"""
from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from paper_analysis.domain.schemas import ParsedDocument


class KeywordQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keyword: str = Field(min_length=1, max_length=200, description="原文关键词或短语")
    max_hits: int = Field(default=3, ge=1, le=5)
    window_chars: int = Field(default=180, ge=20, le=400)


class SectionQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_name: str = Field(min_length=1, max_length=100, description="后端章节名，如 results、method")


class DocumentKeywordSearch(BaseTool):
    name: str = "paper_keyword_search"
    description: str = "在后端绑定的当前证据文档中搜索，返回带定位的原文摘录；无需提交原文。"
    args_schema: type[BaseModel] = KeywordQuery
    _document: ParsedDocument = PrivateAttr()

    def __init__(self, document: ParsedDocument) -> None:
        super().__init__()
        self._document = document.model_copy(deep=True)

    def _run(self, keyword: str, max_hits: int = 3, window_chars: int = 180) -> str:
        query = KeywordQuery(keyword=keyword, max_hits=max_hits, window_chars=window_chars)
        key = query.keyword.strip().lower()
        if not key:
            return "关键词不能为空。"
        blocks = self._document.metadata.get("ordered_blocks", [])
        if not blocks:
            blocks = [{"block_id": "当前文档", "text": self._document.raw_text}]
        snippets: list[str] = []
        for block in blocks:
            text = str(block.get("text", ""))
            start = 0
            while len(snippets) < query.max_hits:
                index = text.lower().find(key, start)
                if index < 0:
                    break
                excerpt = text[max(0, index-query.window_chars):index+len(key)+query.window_chars]
                snippets.append(f"[{block.get('block_id', '未编号')}] 页码 {block.get('page_number', '未提供')}：{excerpt}")
                start = index + len(key)
            if len(snippets) >= query.max_hits:
                break
        return "\n".join(snippets)[:4000] or "当前证据文档中未找到该关键词。"


class DocumentSectionExtractor(BaseTool):
    name: str = "paper_section_extractor"
    description: str = "读取后端绑定的当前证据文档章节，最多返回 4000 字符；无需提交原文。"
    args_schema: type[BaseModel] = SectionQuery
    _document: ParsedDocument = PrivateAttr()

    def __init__(self, document: ParsedDocument) -> None:
        super().__init__()
        self._document = document.model_copy(deep=True)

    def _run(self, section_name: str) -> str:
        query = SectionQuery(section_name=section_name)
        key = query.section_name.strip().lower()
        aliases = {"methods": "method", "experiment": "experimental_setup"}
        key = key if key in self._document.sections else aliases.get(key, key)
        content = self._document.sections.get(key)
        if not content:
            return "未找到该章节；可用章节：" + "、".join(self._document.sections)[:500]
        ids = self._document.metadata.get("evidence_map", {}).get("sections", {})
        return f"[{ids.get(key, key)}]\n{content}"[:4000]


def build_document_tools(document: ParsedDocument) -> list[BaseTool]:
    return [DocumentSectionExtractor(document), DocumentKeywordSearch(document)]
