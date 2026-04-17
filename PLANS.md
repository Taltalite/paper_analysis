# PLANS

## 当前审查结论

- 主执行链路已经不是旧的 `CrewBase` demo，而是：
  `AnalysisService -> CrewAIRuntime -> ResearchPaperPipeline / GeneralTextPipeline -> crew runners`
- 研究论文模式当前已经包含 6 类协作角色：
  - 通用正文 `reader`
  - 通用正文 `analyst`
  - PDF 结构校正 `document_structuring`
  - 图片 grounding `figure_grounding`
  - 图片证据整理 `figure_evidence_curator`
  - 图表分析 `figure_analyst`
- 现有 PDF parser 已经能输出：
  - 顺序化 `text/image blocks`
  - `FigureMetadata`
  - 页截图路径与图片块路径
- 当前仓库已经落地：
  - `FigureSemanticExtractor` 接口
  - `NoopFigureSemanticExtractor` 回退实现
  - `FigureSemanticArtifact` / `FigureEvidence` schema
  - 3 段式图片链路：grounding -> evidence curator -> analyst
- 当前仍未完成的部分是：
  - 真正的 MCP 图片语义工具接入
  - 更高质量的 figure crop / panel 级切分

## 主要缺口

- 仓库内还没有 MCP 驱动的图片语义抽取接口。
- `FigureMetadata` 仅覆盖 caption / page / reference，缺少：
  - 图类型
  - 高质量 panel 划分
  - OCR 文本
  - 坐标轴/图例/表头
  - 方法示意图与结果图的高置信语义标签
- 当前 `figure_grounding` 仍主要依赖 `NoopFigureSemanticExtractor`，只是为 MCP 留好了稳定接入位。

## 推荐方案

推荐加 2 个 agent，而不是只加 1 个。

### 方案 A：最小增量（加 1 个 agent）

- 新增 `figure_grounding_agent`
  - 负责调用 MCP 工具
  - 从 PDF 中定位 figure region
  - 提取 panel / OCR / axis / legend / chart type 等语义证据
  - 输出严格结构化 `FigureEvidenceBatch`
- 保留现有 `figure_analyst`
  - 不再直接猜图
  - 仅基于 `FigureEvidenceBatch + caption + referenced_text_spans` 输出结论

适用场景：
- 先快速验证 MCP 方案是否稳定
- 先控制改动面

### 方案 B：推荐落地（加 2 个 agent）

- 新增 `figure_grounding_agent`
  - 使用 MCP 做 PDF 页面级与区域级图像语义提取
  - 输出每个 figure 的基础证据
- 新增 `figure_evidence_curator`
  - 把 MCP 输出、caption、正文引用、页面上下文合并
  - 归一化为最终 `FigureEvidence`
  - 明确区分“直接可见证据”和“正文声称结论”
- 现有 `figure_analyst`
  - 简化为最终结论生成与图文一致性检查
  - 只消费 `FigureEvidenceBatch`

适用场景：
- 需要长期可维护的论文图片解析链路
- 希望把工具调用、证据整合、结论生成彻底拆开

## 目标结构

建议新增以下模块：

- `src/paper_analysis/adapters/parser/figure_semantics_base.py`
  - 定义 `FigureSemanticExtractor` 接口
- `src/paper_analysis/adapters/parser/mcp_figure_semantics.py`
  - MCP 适配实现
- `src/paper_analysis/runtime/crews/research/figure_grounding.py`
  - figure grounding runner
- `src/paper_analysis/runtime/crews/research/figure_evidence_curator.py`
  - 可选，若采用 2-agent 方案
- `src/paper_analysis/runtime/pipelines/research_paper.py`
  - 接入新的 figure evidence 流程
- `src/paper_analysis/domain/models.py`
  - 新增 `FigureEvidence`、`FigurePanel`、`FigureSemanticArtifact`
- `tests/unit/`
  - 增加 parser adapter、figure pipeline、fallback 路径测试

## 分阶段执行计划

### Phase F1：先把接口补齐

- [x] 新增 `FigureSemanticExtractor` 抽象接口
- [x] 设计 `FigureEvidence` 相关 schema
- [x] 为无 MCP 场景提供 `NoopFigureSemanticExtractor`
- [x] 在 `bootstrap.py` 中以依赖注入方式装配
- [x] 将图片链路重构为 `figure_grounding -> figure_evidence_curator -> figure_analyst`

完成标准：
- 不启用 MCP 时，现有链路行为不变
- 新 schema 与 fallback 测试通过

### Phase F2：接入 MCP 语义抽取

- 让 parser 或 grounding runner 向 MCP 提交：
  - PDF 路径
  - page snapshot
  - image block path
  - caption block / reference block
- 让 MCP 返回可复用结构化结果：
  - figure bbox / crop path
  - panel 切分
  - OCR 文本
  - axis / legend / label
  - 图类型标签
  - 置信度
- 将大图与多 panel 图拆成稳定子区域，避免把整页反复送入 LLM

完成标准：
- 单篇 PDF 的图片语义证据可缓存复用
- figure 级证据结构可脱离 LLM 单独检查

### Phase F3：加入新 agent 协作

- 先落地 `figure_grounding_agent`
- 若采用推荐方案，再落地 `figure_evidence_curator`
- 将现有 `figure_analyst` 改成只做：
  - 实验焦点总结
  - 主要观察归纳
  - claimed conclusion
  - consistency check

完成标准：
- 每个 agent 责任边界单一
- prompt 中不再直接塞整页图像说明文本

### Phase F4：报告与产物升级

- 在 `structured_data` 中增加：
  - `figure_evidence`
  - `semantic_artifacts`
  - `figure_selection_reason`
- 在 markdown 报告中增加：
  - 图像证据摘要
  - 关键 panel 观察
  - 图文冲突项

完成标准：
- 报告可以区分“图像证据”和“作者结论”

### Phase F5：测试与回归

- 为以下内容补测试：
  - schema validation
  - MCP adapter contract
  - figure evidence merge
  - pipeline fallback
  - 无图片 / 多图片 / 多 panel / 方法图 / 结果图
- 用 `input/template.pdf` 走通最小 happy path

完成标准：
- 现有 `research_paper` 文本分析能力不退化
- MCP 不可用时自动回退到 caption + reference 模式

## 关键实现原则

- MCP 负责“切图、识别、布局、OCR、panel 语义”等低层证据抽取。
- LLM 只负责“证据归并、学术语义总结、图文一致性判断”。
- 不要把图片语义直接塞进 `PdfParser` 的核心 `parse()` 主流程里做重逻辑，应通过 adapter 注入。
- 所有新中间结果都要可缓存、可测试、可回退。
- figure 相关结论必须可追溯到：
  - caption
  - referenced_text_spans
  - MCP 结构化证据

## 当前建议的下一步

1. 确认准备接入的 MCP 工具返回格式，尤其是 page region / panel / OCR / chart element 的结构定义。
2. 用真实 MCP adapter 替换 `NoopFigureSemanticExtractor`。
3. 把 figure crop、panel 切分缓存为可复用 artifact，避免重复消耗 token。
