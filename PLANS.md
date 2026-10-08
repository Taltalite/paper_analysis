# PLANS

## 2026-10-05：审核缺口修复与本轮验收

- [x] HTTP request/response 计量接入，禁用 SDK 隐式重试，文本/视觉输出限额贯通；账本逐请求落盘并跨 attempt 复用。
- [x] 修复不确定性与领域报告泄漏、章节证据注册、部分 usage 丢失；新增回归测试。
- [x] 加入领域提示与证据绑定、报告有界补取/直接图像复核、同文档会话与共享预算、报告子进程主管、Web 策略与用量界面。
- [x] 新增故障/会话接口测试、CI/批测门禁和浏览器测试；137 项单元、6 项集成、2 项浏览器交互通过。
- [x] Kimi/Qwen 合成接口 smoke：2 次请求，共 1,600 实际 tokens，预算 8,000；前端构建通过。
- [x] 验收映射和已知限制写入 `docs/PLAN_FIXES_2026-10-05.md`；不把适配器 smoke 视为完整真实论文验收。

下一步：在固定论文样本上运行报告/问答真实全链路与领域专项矩阵；专家效果仍 `not_evaluated`。本轮不宣称原计划所有科学质量或真实场景已经验收。

## 2026-10-05：独立计划审核与 smoke test

- [x] 对照 WP-00～WP-11 审核代码和验收条件；结论：**未完成全部计划**。下方已勾选的基础实现不代表完整工作包验收通过。
- [x] 沙箱外复验：122 项单元、6 项 API 集成通过；前端生产构建通过。沙箱内两套测试超时，未记为通过。
- [x] 9 项计划约束离线探针：2 项通过、7 项暴露缺口；涉及预算边界、正式输出泄漏、章节引用和部分 usage。
- [x] Kimi / Qwen 合成输入真实 smoke 均通过，两次实际请求合计 1578 tokens；未发送论文，不等于完整 PDF agent loop 验收。
- [ ] 按审核 F1～F7 修复，再补齐 WP-08～WP-11；本次审核未改业务实现。

详见 [计划审核与测试报告](docs/PLAN_AUDIT_2026-10-05.md)。

## 2026-10-04：项目改进实施进度（WP-00～WP-07 基础能力）

- [x] WP-00：建立本次基线报告，记录 Python / Pydantic / FastAPI / CrewAI / PyMuPDF 版本、命令结果和未完成原因，见 [docs/BASELINE_2026-10-04.md](docs/BASELINE_2026-10-04.md)。
- [x] WP-01：新增执行策略、模型能力、TokenUsage、CallRecord、ExecutionSummary、CoverageReport，以及故事线、图组 Flow、证据矩阵和 Benchmark schema；旧请求字段保持可选兼容。
- [x] WP-02：新增线程安全 `BudgetLedger`，接入视觉 OpenAI-compatible 适配器、问答文本阶段和报告 CrewAI 阶段；区分 provider / estimated / unknown / cache 命中，预算拒绝发生在发送前。
- [x] WP-03：分析任务与问答任务持久化 requested/effective policy、execution summary 和 stop reason；结果与审计共用策略版本和配置指纹。
- [x] WP-04：视觉复核失败细分为缺图、预算、超时、HTTP、解析和供应商错误；视觉主张仍必须通过直接图像复核才能发布。
- [x] WP-05：基于已有 parser、claim inventory 和 QC 确定性组装故事架构、图组 Flow、细节证据矩阵、Benchmark 和覆盖报告，并新增报告第 11 节；不适用/未报告保持可区分。
- [x] WP-06～WP-07：问答策略控制补取/选图/视觉复核上限；报告和问答复用 parser 资产与证据闸门，报告文本、图表分析和事实核验阶段纳入共享账本。
- [x] 增加执行契约、预算账本、领域产物和现有 PDF / 视觉 /报告链路的离线回归。
- [ ] WP-08：连续追问会话、turn 版本和跨 turn 预算仍未实现。
- [ ] WP-09：报告任务仍使用进程内线程池，取消/超时尚未达到问答子进程同等的强制终止保证。
- [ ] WP-10～WP-11：前端策略/用量/领域视图和完整故障矩阵门禁仍待补齐；当前没有进行新的真实模型调用或专家效果评估。

本轮实施细节、测试退出码和已知限制见 [docs/IMPLEMENTATION_PROGRESS_2026-10-04.md](docs/IMPLEMENTATION_PROGRESS_2026-10-04.md)。工作区中原有未提交文件和历史记录均保留。

## 2026-10-04：领域定位与无人工标注工程闭环（规划记录；实施进度见上节）

> 本节保留规划交接时的目标和边界；当前完成项与未完成项以本文件上方的“项目改进实施进度”为准。

- [x] 审计现有代码和历史真实冒烟，保留当前未提交成果。
- [x] 确定 Kimi 文本 + Qwen `qwen3.8-flash` 图像，面向分子生物学、生物信息学与表观遗传学。
- [x] 按用户要求完成规划者交接文档：12 个工作包、契约、依赖、测试矩阵和验收标准。
- [x] 实施 agent 已从 WP-00 基线与 WP-01 契约开始，并按依赖推进统一预算与领域产物；当前未完成项见上方实施进度。
- [ ] 完成全部离线回归与工程指标验收；当前已分层通过 109 项单元测试和 Web 构建，FastAPI TestClient 环境问题及剩余生命周期验收见上方进度。

实施主计划见 [项目改进与 agent 交接计划](docs/PROJECT_IMPROVEMENT_PLAN_2026-10-04.md)，摘要见 [工程目标](docs/ENGINEERING_TARGET_2026-10-04.md)。这里的规划说明不把设计自动计为完成实现；具体实现以本文件上方进度和测试证据为准。下方历史“下一步需人工标注”仅针对领域效果评估，不阻塞当前工程工作。

## 2026-10-03：Qwen 冒烟与人工标注材料

- [x] 生成 `evals/annotation/blank.json`、当前论文五份待标注任务及逐步说明，保留旧模板兼容。
- [x] Qwen 真实冒烟：用户补齐 Token Plan 地址后，发现 qwen3-vl-flash 不受支持；改用 qwen3.8-flash 完成合成图及五场景论文冒烟。本地模型名已更新，详见 `docs/QWEN_SMOKE_2026-10-03.md`。
- [ ] 修复不确定性说明中残留未核验断言、细分视觉复核失败审计；用人工标注评估目标子图/高分辨率改进，当前不能认定视觉准确率达标。

## 2026-10-03：Kimi 文本 + Qwen 视觉配置模板

- [x] 根据百炼官方文档更新 `.env.example` 与 README：Kimi Code 文本、Qwen3-VL-Flash 视觉、业务空间专属 OpenAI 兼容 URL，密钥留空。
- [x] 明确地域/业务空间替换、Plus 对比选项和独立计费；不覆盖用户 `.env`。
- [x] 已使用用户实际 Token Plan 接口完成冒烟；小字/上标仍存在误读，正式标签主张拒答，详情见本日 Qwen 冒烟记录。

## 2026-10-03：agent 流程与有界循环完善（进行中）

- [x] 独立视觉供应商配置，问答/报告共用统一适配器；缓存与审计区分视觉目的地。
- [x] 补齐证据缺口停止条件，避免不可补救的视觉缺口反复消耗调用。
- [x] 验证多轮纠错、冲突撤回与后续技术失败组合，防止旧主张复活。
- [x] 报告正文 12,000 字符硬上限，关键词/章节工具改为后端绑定文档且限制输出；去除重复问答提示。
- [x] 修复报告任务快速完成时 Future 回调与主管锁的死锁。
- [x] 问答增加直接看图复核、目标子图提取与独立缓存；每题两次复核上限，未获支持的视觉主张不交付。
- [x] 工程清单新增最终视觉主张复核、复核预算和模型错误检查，不替代人工金标准。
- [x] 覆盖问答纠错、复核漏项/失败/预算/缓存及真实 API 装配；原报告与异步路径回归通过，更新 README。

保留已有真实冒烟与历史产物；新供应商未配置前使用 fake 验证装配，不自动切换真实密钥/目的地。

本阶段验证：111 项单元、6 项 API 集成通过，前端生产构建通过。使用原有 Kimi 配置复验目标子图与关闭视觉两场景：分别 151.514 秒/1 轮、22.728 秒/1 轮，八项工程检查均通过。结果见 `evals/runs/qa-loop-review-2026-10-03/manifest.json`。独立视觉配置模板为 `.env.example`，用户本地 `.env` 未修改。下一步仍需人工标注后的评分器与模型对比；全文报告未加入本次问答专用的直接看图复核，不宣称全系统视觉错误已消除。该段为历史记录，不替代本次基线和实施验证。

## 2026-10-03：真实问答冒烟完成，视觉质量问题待改进

- [x] 使用用户本次提供的 PDF 和 Kimi Code 配置完成四场景真实冒烟，最多两轮补取；工程检查通过。
- [x] 核查正文引文、实际视觉输入页、缺图拒答与关闭视觉降级。
- [ ] 修复/改进视觉 OCR 错误经摘录核验后进入答案的问题；目标子图不确定性过滤及无视觉停止策略待优化。
- [ ] 专家标注、评分器、基线对比和领域效果验证仍未完成。

结果详见 `docs/QA_SMOKE_2026-10-03.md`。下方 2026-09-28 的“待授权/未执行”是历史状态；本次新 PDF 指纹独立记录，旧清单保留。


## 2026-09-28：问答 P0–P2 工程闭环

- [x] P0：严格主张引文/来源/子图交付闸门；定向补取、停滞停止；技术调用失败保留先前部分答案，新增冲突不得恢复旧主张；逐轮审计。
- [x] P1：持久化后台任务、进度、超时终止、失败重试及重启恢复；兼容同步问答；PDF 页/块定位与实际视觉输入查看。
- [x] P1/P2：按 PDF 指纹和解析版本复用解析，按需渲染页面；缓存失效及并发回归。
- [x] P2 工具：批量候选与独立运行清单，配置失败/运行失败分别记录；四场景无模型准备检查通过。
- [ ] 真实正文/子图/缺图/无视觉冒烟：命令因具体 PDF 与模型目的地外发确认被自动审批拒绝，未执行；已请求用户确认 MoDorado PDF → api.kimi.com / kimi-for-coding。不得绕过，也不得计作真实调用成功。
- [x] 工程验收：96 项单元测试、5 项 API 集成测试通过；前端构建与 git diff --check 通过。新增扫描/损坏 PDF、并发缓存、故障及配置失败回归；无专家效果评分。
- [x] 按用户要求固化可恢复文档 `docs/QA_AGENT_P0_P2_CHECKPOINT_2026-09-28.md`；工程验收说明见 `docs/qa-engineering.md`。

任务状态由后端管理；不引入外部检索、训练或重型队列。超时必须阻止迟到结果发布；审计与最终证据需指向同一 PDF 指纹。人工标注不作为以上工程工作的前置条件。

## 2026-09-28：单篇生物信息与表观遗传学图表问答

按已有解析、视觉和 QC 能力增量实现，保留全文报告及 `/api/analysis`。

- [x] 阶段 A：类型化问题、回答、证据定位协议；独立 CrewAI runner / pipeline / service；单轮可用（max_followups=0）。
- [x] 阶段 B：最多两次文内证据补取与 QC 反馈纠错；正文预算、目标图/子图视觉来源检查。
- [x] 阶段 C：新增 `/api/qa/questions`，后端持久化 PDF、解析结果、请求和答案；最小中文问答 UI。
- [x] 阶段 D：83 项单元测试、3 项 API 集成测试通过，前端生产构建通过；新增 12 项问答单元测试与 1 项 API 集成测试。沙箱异步唤醒受限时改用获准的沙箱外离线回归。
- [x] 准备 16 条候选（12 条待绑定领域题型、4 条绑定本地 MoDorado PDF 与具体子图），人工标注模板及验证边界文档。仅核对本地图注文本，没有新增真实问答调用或专家评分。

验收标准：不调用全文报告；正常正文回答可定位到 PDF 页/块；视觉失败不交付视觉主张；错误引用被 QC 阻止；缺失图/子图返回部分回答或拒答；最多 3 轮生成/核验；旧 API 回归通过；前端构建成功。所有测试使用 fake 或合成 PDF，不把离线测试算作真实模型调用或领域效果验证。

边界：本轮不加入外部检索、多论文综述、模型训练；同步问答接口适用于本地版本。候选集不是专家金标准。下一步由专家绑定实际论文与逐条证据、双人标注后评估真实调用效果。

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
- [ ] 完善证据 ID 重建与语义核验闭环（视觉字段传递及 QC v1 报告交付闸门已完成，见下方记录）。
- [ ] 实现离线评估 schema、确定性评分器、基线对比和 CI 回归门禁。
- [ ] 在用户批准模型与预算后，对校准集运行真实模型评估。

## 下一步候选方向

- 多模态串行真实 API smoke 已完成（见下方审计记录）；按需单独验证并行开关的端到端质量
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
- [x] 完成公开论文的无视觉基线与完整多模态运行：`output/audit-complete.*`，4/4 图表为真实视觉来源、4 项图表分析、16 项事实核验。
- [x] 完成 2 项 API 集成测试并记录本次简历能力审计结论（`docs/project-capability-audit.md`）。
- [x] 2026-09-08 收尾：修复 Markdown 主模板未调用视觉证据展示函数的问题，强化既有核心测试以检查 `render()` 公开入口；复用真实输出重新渲染产物，不增加模型调用。

边界：保留 CrewAI 和既有 API；尚未完成医学专项质量评估、外部 RAG 或精确逐图裁剪，不据此宣称临床应用效果或量化降幻觉收益。

## QC v1：可独立完成的质量闸门

- [x] 抽取共用主张清单，保留 20 条事实核验预算，对超出清单明确报告未核验。
- [x] 核验漏项、重复、未知主张 ID、文本错配、无效证据与证据片段定位检查。
- [x] 将字符串 evidence 规范为数组，修复真实旧输出中原始主张被跳过的问题；历史产物不伪造重新核验结果。
- [x] 添加统一 QualityReport；独立于任务执行状态保存，并通过任务、报告、产物接口返回。
- [x] 主模板执行交付闸门；正式摘要由可交付主张原句构成，未绑定生成字段转为待复核，保留 qc_draft。
- [x] 保留 parser 原始章节证据、记录证据索引指纹，证据变化时阻止复用旧核验。
- [x] 提供离线 QC 命令，复用已有真实结果生成 output/audit-qc.*，全程无新增 LLM 调用。
- [x] 完成回归：71 项单元测试、2 项 API 集成测试通过；仅新增 4 项核心测试，并强化既有 API 测试。
- [x] 离线产物核对：有效核验清单 16 条，另有 15 条旧格式无效主张；2 条满足交付规则，质量状态 needs_review，未获支持的 DTW 描述已从正式摘要移至草稿。原报告未覆盖。

下一步：由用户确认少量原文事实与报告错误，建立检测准确性金标准；再改进数值 / 单位 / 实验条件核对及语义绑定。当前规则通过不等于内容正确性认证。
