# PLANS

## 当前架构结论

研究论文模式已从 6 个常驻角色收敛为 3 个核心 agent：

- `text_understanding`
  - 合并原 `reader + analyst`
  - 一次完成正文理解、要点提取、综合分析
  - 输出带原文章节和证据片段的 `claims`，核心 claim 需引用稳定 evidence ID
- `figure_understanding`
  - 消费统一 `FigureEvidenceBatch`
  - 输出图表观察、作者主张和图文一致性分析
  - 低层 semantic extraction 由 adapter 负责
- `fact_checker`
  - 在文本和图表分析之后执行
  - 对每条主张输出 verdict、evidence refs、evidence IDs、rationale 和 confidence
  - 前置确定性规则预检查（`fact_check_prechecks`），flags 随 prompt 注入并写入报告

`document_structuring` 保留为条件式结构修复任务，不再对结构完整的 PDF 固定调用。

LLM 适配以 Kimi API 为主（OpenAI 兼容协议），`KIMI_*` 环境变量优先，`OPENAI_*` 保留回退。
图表语义 adapter 路线已确定为多模态 LLM（`MultimodalFigureSemanticExtractor`），
`MCPFigureSemanticExtractor` 保留为占位契约。旧 `figure_grounding` / `figure_evidence_curator`
的 CrewAI 实现、旧两 agent runner、`ContentCrew` 与占位 `runtime/flows` 已删除。

默认研究论文路径的常规 LLM 阶段为：

1. `text_understanding`
2. `figure_understanding`（存在可分析图表时）
3. `fact_checker`

结构不完整时，前置增加一次 `document_structuring` 修复任务。
设置 `PAPER_ANALYSIS_PARALLEL_STAGES=1` 后，`text_understanding` 与 `figure_understanding`
两个 LLM 阶段通过 CrewAI 原生 `kickoff_async` 并行（默认仍串行）。

## Phase 4 已完成

### Kimi-first LLM 适配

- [x] `KIMI_API_KEY` / `KIMI_MODEL` / `KIMI_BASE_URL` / `KIMI_TEMPERATURE` / `KIMI_VISION_MODEL` 优先解析，默认 `https://api.moonshot.cn/v1` + `kimi-k3`
- [x] `OPENAI_*` 回退兼容，缺 key 时保持中文 fail-fast
- [x] `VisionLLMClient` 协议 + `complete_with_images`（OpenAI 兼容 image_url，base64 data-URI）
- [x] `scripts/run.sh` 默认 `NO_PROXY` 加入 `api.moonshot.cn` / `api.moonshot.ai`

### Phase M1：真实图表语义 adapter（多模态 LLM 路线）

- [x] 确定多模态服务契约（OpenAI 兼容 image_url；MCP 契约保留为占位）
- [x] 传递 figure crop 实际图片内容（base64），不再只传路径字符串
- [x] 支持 OCR（visible_text）、panel、axis、legend 与置信度；table 类内容经 visible_text / direct_evidence 表达
- [x] semantic artifact 缓存键（图片字节 sha256 + vision model + prompt 版本），落盘 `.paper_analysis_assets/<stem>/semantic_cache/`
- [x] 失败保守回退 Noop，不中断 pipeline

### Phase M2：事实检查增强

- [x] parser 为 section 生成稳定 evidence ID（`S1..Sn`），图表沿用 `figure_id`，block 沿用 `block_id`；写入 `metadata["evidence_map"]` 与结构化 markdown「证据索引」
- [x] `ClaimEvidence` / `FactCheckItem` 增加 `evidence_ids`；prompt 要求核心 claim 引用 evidence ID；缺失者由规则预检查标记
- [x] 确定性规则预检查：数值一致性（原文+图表证据）、证据片段回指、缺失 evidence ID 引用（数据集/指标名为浅启发式，见限制）
- [x] 外部事实检查定义为可选 `RetrievalAdapter` 协议（`adapters/retrieval/`），默认不装配、不与核心硬耦合

### Phase M3：兼容清理

- [x] 删除旧 `ContentCrew`（`src/paper_analysis/crews/`，已确认无引用）
- [x] 删除两 agent 默认实现 `two_agent_text_analysis.py`（协议移入 `text_understanding.py`）
- [x] 删除旧 CrewAI 版 `figure_grounding` / `figure_evidence_curator` crew（保留 adapter / 确定性实现）
- [x] 清理占位 `runtime/flows`
- [x] 拆分 `ResearchPaperPipeline` 报告渲染职责（`research_paper_report.py` 的 `ResearchPaperReportRenderer`，pipeline 785 → 392 行）

### Phase M4：测试与运行可靠性

- [x] 多模态 adapter contract 测试（mock vision client：JSON 解析、code fence、fallback、缓存命中/未命中、多图截断）
- [x] 无图、多图（选图上限 4）、多 panel、Table 类、证据冲突（数值冲突 flags）案例
- [x] 三 agent 完整 happy path（fake runners 注入）+ 并行路径测试
- [x] `input/template.pdf` fixture 改为测试内 pymupdf 生成（红灯消除）
- [x] 修复 `TimestampedLogWriter` 对关闭流 `flush()`/`write()` 的清理异常
- [x] CrewAI 原生 `kickoff_async` 专项验证：Python 3.13 下协程正常调度、错误可传播（无挂起）；并行路径作为可选开关引入（`PAPER_ANALYSIS_PARALLEL_STAGES`，默认串行）

## 当前限制

- 未配置 `KIMI_VISION_MODEL` 时，`NoopFigureSemanticExtractor` 仍仅依据 caption 和正文引用生成低置信度语义。
- `MCPFigureSemanticExtractor` 仍是占位实现，未接真实 MCP server。
- 规则预检查是浅启发式：数值以子串匹配核对，数据集/指标名未做实体级交叉核对。
- 当前事实检查是论文内部证据核验，不访问外部论文库或 DOI 数据源（`RetrievalAdapter` 仅定义协议）。
- 并行模式下 figure grounding（视觉 HTTP 调用）仍在事件循环内同步执行，只有 `text_understanding` 与 `figure_understanding` 两个 LLM 阶段真正并行；该开关尚未经过真实 API 端到端验证。

## Phase E1：可量化评估基础（进行中）

- [x] 建立 `paper_v1` 私有校准集清单：4 篇用户提供 PDF，记录路径、SHA-256、DOI、页数和难度标签，不复制原始论文。
- [x] 建立人工标注模板：每篇 8--12 条核心主张，使用页码/章节定位，并包含用于验证“待核验”渲染策略的负例。
- [ ] 修复证据 ID 重建、事实检查报告闸门等可信闭环问题（视觉语义字段传递已在 2026-09-07 补齐）。
- [ ] 实现离线评估 schema、确定性评分器、基线对比和 CI 回归门禁。
- [ ] 在用户批准模型与预算后，对校准集运行真实模型评估。

## 下一步候选方向

- 真实 API smoke：配置 `KIMI_API_KEY` + `KIMI_VISION_MODEL` 跑 `bash scripts/run.sh`，验证多模态图表语义与并行开关的端到端质量
- 规则预检查深化：数据集/指标名的实体级核对、图文数值冲突双向比对
- 按需实现 `RetrievalAdapter` 的具体外部数据源（DOI / 论文库）
- 视真实运行情况决定并行路径是否转为默认

## 2026-09-07：简历能力审计与多模态链路补全

- [x] 运行修复前单元测试：59 项通过；真实 CLI 首次运行暴露工作区外 CrewAI memory 目录不可写问题。
- [x] `scripts/run.sh` 支持 Python / 测试命令并设置工作区内 XDG_DATA_HOME，保留不带参数的 kickoff 行为。
- [x] 确认原本地配置未启用视觉模型；用当前 Kimi Code 账号真实识别合成柱状图，读出提示词之外的 Alpha / Beta / 37 / 83。
- [x] 更正 README 中“Kimi Code 不支持视觉”的错误说明；本地 `.env` 显式启用已验证的 `kimi-for-coding` 视觉模型。
- [x] 优先使用完整页面渲染，保留矢量图、坐标轴、文字及全部子图；同路径 PDF 重解析时刷新页面截图。
- [x] 补齐 OCR、图例、子图信息向图表分析、内部核验和 Markdown / JSON 的传递。
- [x] 结构修复后恢复 parser 生成的图片路径，保留遗漏图表，不使用模型生成的本地文件路径。
- [x] 视觉失败显示原因、noop 不冒充 OCR、无效输出不缓存、正文引用变化使缓存失效。
- [x] 添加显式真实视觉自检脚本及 8 项离线回归测试，当前 67 项单元测试通过。
- [x] 真实论文运行发现 Figure 4 图形在第 7 页、图注在第 8 页；补齐相邻页关联后真实复验识别 a–g 共 7 个子图。
- [x] 为复杂多面板图增加 `VISION_REQUEST_TIMEOUT`；Figure 2 首次 120 秒超时，240 秒配置复验成功，返回 5 个子图。
- [ ] 完成公开论文的无视觉基线与完整多模态运行，核对最终产物。
- [x] 完成 2 项 API 集成测试并记录本次简历能力审计结论（`docs/project-capability-audit.md`）。

边界：保留 CrewAI 和既有 API；尚未完成医学专项质量评估、外部 RAG 或精确逐图裁剪，不据此宣称临床应用效果或量化降幻觉收益。
