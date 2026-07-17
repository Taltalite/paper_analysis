# PLANS

## 当前架构结论

研究论文模式已从 6 个常驻角色收敛为 3 个核心 agent：

- `text_understanding`
  - 合并原 `reader + analyst`
  - 一次完成正文理解、要点提取、综合分析
  - 输出带原文章节和证据片段的 `claims`
- `figure_understanding`
  - 消费统一 `FigureEvidenceBatch`
  - 输出图表观察、作者主张和图文一致性分析
  - 低层 semantic extraction 由 adapter 负责
- `fact_checker`
  - 在文本和图表分析之后执行
  - 对每条主张输出 verdict、evidence refs、rationale 和 confidence

`document_structuring` 保留为条件式结构修复任务，不再对结构完整的 PDF 固定调用。

原 `figure_grounding` 和 `figure_evidence_curator` 的 CrewAI 实现暂时保留用于兼容，但默认服务已经改用：

- `AdapterFigureGroundingRunner`
- `DeterministicFigureEvidenceCurator`

因此默认研究论文路径的常规 LLM 阶段为：

1. `text_understanding`
2. `figure_understanding`（存在可分析图表时）
3. `fact_checker`

结构不完整时，前置增加一次 `document_structuring` 修复任务。

## 已完成

- [x] 增加 `ClaimEvidence`、`FactCheckItem`、`FactCheckBatch` schema
- [x] 新增单 agent `CrewAITextUnderstandingRunner`
- [x] 默认服务不再装配两段式正文 Crew
- [x] figure grounding 降为 adapter 调用
- [x] figure evidence curator 降为确定性合并
- [x] 新增 `CrewAIFactCheckRunner`
- [x] 事实检查结果写入 JSON `structured_data`
- [x] Markdown 报告增加“事实检查”章节
- [x] PDF 结构校正改为条件触发
- [x] 保留旧 runner 和协议，避免静默破坏已有依赖注入代码
- [x] 增加事实检查 schema、fallback 和 pipeline 测试

## 当前限制

- 默认 `NoopFigureSemanticExtractor` 仍主要依据 caption 和正文引用生成低置信度语义。
- `MCPFigureSemanticExtractor` 仍是占位实现，尚未完成真实图片 OCR、panel、axis、legend 和 table extraction。
- 当前事实检查是论文内部证据核验，不访问外部论文库或 DOI 数据源。
- 文本、图表和事实检查当前按顺序执行。Python 3.13/CrewAI 环境下的 `asyncio.to_thread()` 并发桥接存在事件循环无法唤醒的问题；在 CrewAI 原生异步调用通过专项验证前，不启用该并行路径。
- 旧 `ContentCrew` 和占位 `runtime/flows` 尚未删除。

## 下一阶段

### Phase M1：真实图表语义 adapter

- [ ] 确定 MCP / 多模态服务契约
- [ ] 传递 figure crop 或受支持的图片内容，而不是仅传本地路径字符串
- [ ] 支持 OCR、panel、axis、legend、table cell 与置信度
- [ ] 为 semantic artifact 增加缓存键，避免重复处理图片

### Phase M2：事实检查增强

- [ ] 为 parser block 和 section 生成稳定 evidence ID
- [ ] 要求所有核心 claim 引用 evidence ID
- [ ] 增加数值、数据集、实验设置和图文冲突的规则预检查
- [ ] 将外部事实检查设计为可选 retrieval adapter，不与核心服务硬耦合

### Phase M3：兼容清理

- [ ] 完成迁移周期后删除旧 `ContentCrew`
- [ ] 删除不再使用的两 agent 默认实现或移入 legacy 包
- [ ] 清理占位 `runtime/flows`
- [ ] 拆分过大的 `ResearchPaperPipeline` 报告渲染职责

### Phase M4：测试与运行可靠性

- [ ] 补真实 MCP adapter contract 测试
- [ ] 补无图、多图、多 panel、Table 和证据冲突案例
- [ ] 补 mock LLM 的三 agent 完整 happy path
- [ ] 恢复缺失的 `input/template.pdf` 测试 fixture 或改为测试内生成
- [ ] 修复 `TimestampedLogWriter` 对关闭流执行 `flush()` 的清理异常
- [ ] 验证 CrewAI 原生 async kickoff 后再考虑并行文本与图表阶段
