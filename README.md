# Paper Analysis

面向分子生物学、生物信息学与表观遗传学的 CrewAI 文献分析平台：Kimi 处理论文文字和综合分析，Qwen `qwen3.8-flash` 处理图像输入。重点分析论文故事架构、图组论证流程、结果证据支持，以及多方法比较论文的 benchmark。支持本地文件、FastAPI 后端和轻量 Web 前端。

当前工程目标是在不依赖人工标注的情况下打通 agent loop、证据问答、token 预算和分析强度控制。实施工作包、依赖和测试要求见 [项目改进计划](docs/PROJECT_IMPROVEMENT_PLAN_2026-10-04.md)，进度与验收边界见 [工程目标](docs/ENGINEERING_TARGET_2026-10-04.md)；工程测试通过不等于专家效果评估通过。

2026-10-05 已补入请求级计量与持久化累计预算、报告补取及直接图像复核、后端连续问答、可终止的报告子进程、Web 策略控制和离线 CI。修复映射、复现命令与尚未验收的范围见 [本轮修复验收](docs/PLAN_FIXES_2026-10-05.md)，该记录更新下文历史里程碑的能力边界。

报告创建接口支持 `intensity`、`token_budget`、`max_calls`、`max_output_tokens`、`timeout_seconds`、`report_followups`。报告补取默认 0，Web 默认 1，最多 2；每次新增候选须重新核验。`light/standard/deep` 控制系统迭代与证据范围，不代表供应商原生 reasoning 参数已启用。显式填写的预算不会随强度提高。

`POST /api/qa/questions/{id}/conversation` 从已完成问答创建会话，`GET /api/qa/conversations/{id}` 恢复会话，`POST /api/qa/conversations/{id}/turns` 接收 `QuestionRequest` JSON，无需再上传 PDF。会话按顺序追问并累计用量；重试不清零账本。报告可通过 `/api/analysis/jobs/{id}/cancel` 和 `/retry` 取消、重试。当前本地队列只支持一个 API 主管进程。

真实接口 smoke 使用合成材料，运行命令为 `bash scripts/run.sh python -m scripts.smoke_models --output output/new-smoke-directory`，最多 2 次请求，共享 8,000 token 预算；默认 CI 不执行该命令。未知供应商用量按预留保守记账，估算与实际用量分别显示，不能把预算估算当成精确费用上限。

系统面向的核心场景是：
- 读取 `txt` / `md` / `pdf`
- 解析论文结构与图表信息
- 生成简体中文为主的 Markdown / JSON 分析结果
- 通过后端 job 接口统一管理任务状态与产物

## 架构概览

### 单篇文献图表问答

Web 页面顶部提供生物信息与表观遗传学问答：上传单篇 PDF、输入问题，可指定图号（如 `2`）和子图（如 `a`）。无需创建全文报告任务，原有报告与 `/api/analysis` 接口保留。

新增 `POST /api/qa/questions`（multipart）：`file`、`question`、可选 `figure` / `panel`、`max_followups`（0–2，默认 2）。设为 0 即单轮问答；2 表示初次回答后最多两轮文内补取与纠错。同步返回类型化答案，`GET /api/qa/questions/{id}` 读取后端保存结果。

分析和问答请求还可提交 `intensity`（`light` / `standard` / `deep`）、`token_budget`、`max_calls`、`max_output_tokens`、`timeout_seconds`、`max_figures` 和 `max_visual_reviews`。后端会保存 requested/effective policy、调用数量、provider/estimated/unknown 用量、缓存命中和 stop reason；强度档位不会绕过服务端上限。

返回 `status`（`answered` / `partial` / `refused`）、中文 `answer`、逐条 `claims` 与 `evidence_ids`、`evidence` 的 PDF 物理页码/正文块/图号/子图/原文摘录、`uncertainties`、`visual_status` 和 `quality`。审计中的 `visual_review.failure_reason` 会区分缺图、预算耗尽、截止时间、HTTP、解析和供应商错误。页面视觉证据为模型观察，记录实际输入页码集合，不等同于专家金标准。未成功读取目标图/子图时不得交付视觉主张；正文/图注可支持部分回答。

独立链路为 PDF parser → 文内块检索 → 按需视觉 adapter → CrewAI 问答 → 既有事实核验和 QC → 有界纠错。每轮新增最多四个正文块，每块最多 1500 字符；视觉仅针对一个目标图。显式图号优先，也支持从问题提取 `图2a` / `Figure 2a`。未指定图号时按图注关键词选择候选图；复杂定位或扫描图注可能失败，应指定图号或核对原文。问答解析阶段只建结构索引，目标页首次读图或查看证据时才渲染；全文报告的默认解析行为不变。

后端在 `.data/questions/{id}/` 保存 PDF、请求、任务状态、解析视图、逐尝试审计与最终答案。最大 PDF 为 30 MB。Web 默认使用后台问答队列，可取消、重试，在刷新后从后端任务列表恢复；URL 中只保存任务 ID，不在浏览器保存业务结果。LLM / 视觉配置沿用统一适配器，不加入外部检索、多论文综述或训练。

- `POST /api/qa/jobs`：同样的 multipart 字段，返回 202 和任务 ID。
- `GET /api/qa/jobs`、`GET /api/qa/jobs/{id}`：最近任务及执行阶段。
- `POST /api/qa/jobs/{id}/cancel`、`POST /api/qa/jobs/{id}/retry`：取消和失败恢复。
- `GET /api/qa/questions/{id}`：正式答案，任务完成前不发布。
- `GET /api/qa/questions/{id}/audit`：当前尝试的逐轮证据、草稿、核验和 QC。
- `GET /api/qa/questions/{id}/pages/{page}?evidence_id=...`：PDF 物理页 PNG，正文证据可高亮原始 bbox；视觉证据可查看实际输入页。

原同步 `POST /api/qa/questions` 保留，通过同一个队列等待结果，超时返回 504。当前是 Linux 单 API 主管进程的本地版本（勿使用多个 Uvicorn workers），默认同时运行 2 个问答子进程，单任务执行上限 600 秒。超时/取消终止子进程；异常重启后运行中的任务标为失败，排队任务恢复，用户可显式重试。重试递增 attempt 并保留旧审计；迟到或旧轮次产物不能覆盖最终状态。具体工程验收见 [docs/qa-engineering.md](docs/qa-engineering.md)。

离线验证：

```bash
bash scripts/run.sh python -m unittest discover -s tests/unit -v
bash scripts/run.sh python -m unittest discover -s tests/integration -v
bash scripts/run.sh npm --prefix web run build
```

领域候选集及人工标注规则见 [evals/qa_README.md](evals/qa_README.md)。本轮未进行真实问答模型调用或专家效果评估；测试通过仅说明实现和失败处理符合离线验收，不代表领域答案已被验证正确。

### 目录结构

- `src/paper_analysis/domain/`
  领域模型、枚举、输入输出 schema
- `src/paper_analysis/adapters/`
  LLM、parser、storage 适配层
- `src/paper_analysis/runtime/`
  CrewAI runtime、analysis pipeline、research agents
- `src/paper_analysis/services/`
  分析编排、artifact 持久化、job 生命周期管理
- `src/paper_analysis/api/`
  FastAPI 应用、依赖注入与路由
- `web/`
  React/Vite 前端
- `input/`
  示例输入文件
- `output/`
  本地运行输出

### 分析链路


默认分析链路收敛为 3 个核心 agent / role：

- `text_understanding`
  一次完成重点章节理解、事实性要点提取、论文综合分析，并输出可追溯的 `claims`
- `figure_understanding`
  基于 parser / 视觉语义 adapter 与确定性证据合并结果，输出图表观察、作者结论和图文一致性分析
- `fact_checker`
  独立核验正文与图表分析产生的主张，输出证据引用、判定、理由和置信度

`document_structuring` 不再作为常驻核心 agent。它是条件式结构修复任务，仅在标题、摘要、核心章节或 figure caption 缺失，或 parser 明确标记低置信度时触发。

原 `reader + analyst` 已合并为 `text_understanding`；原 `figure_grounding` 的低层抽取改由 adapter 负责，`figure_evidence_curator` 改为确定性合并逻辑，不再分别消耗 LLM 调用。旧 runner 与 `ContentCrew` 等兼容实现已完成迁移并删除。

PDF 文献分析的当前执行顺序为：

1. 通过 parser 读取源文件。
2. 对 PDF 按阅读顺序提取 text/image blocks。
3. 使用规则生成粗结构草稿：
   标题、作者、摘要、章节、figure caption、正文引用关系。
4. 仅在粗结构不完整时调用 `document_structuring` 修复任务。
5. 使用 `text_understanding` 生成正文分析和可追溯主张。
6. 通过 figure semantic adapter 和确定性 assembler 生成统一图表证据，再由 `figure_understanding` 分析图表。
7. 使用 `fact_checker` 对正文与图表主张做统一内部证据核验。
8. 输出最终 Markdown、JSON，以及 PDF 的结构化 Markdown 中间产物。

未配置视觉模型时，figure semantic adapter 是 `NoopFigureSemanticExtractor`，只使用图注和正文线索，不产生 OCR 结果。配置 `KIMI_VISION_MODEL`（或 `OPENAI_VISION_MODEL`）后启用 `MultimodalFigureSemanticExtractor`，真实发送 base64 图片并提取 OCR、坐标轴、图例与子图信息。PDF 优先发送 2 倍分辨率的完整页面渲染并指定目标图号，避免只读嵌入位图时丢失矢量坐标轴或部分子图；没有页面截图时才使用可读的嵌入图片（最多 4 张）。当前不是精确的逐图区域裁剪。

视觉字段会传入图表分析、内部事实核验和最终 Markdown / JSON。报告明确显示是否完成视觉识别及失败原因；HTTP / 输出格式失败时保守回退，不能把报告生成成功等同于图片解析成功。图表语义缓存包含图片内容、模型、图号、图注和实际提示词（含正文引用）；更换同路径 PDF 时会重新生成页面截图。

针对“前页整页图、后页顶部图注”的排版，parser 会在图注页缺少图形、前页存在明显图形且无其他图注时，补充前页截图。`FigureMetadata.page_number` 仍表示图注页，新增 `context_page_snapshot_paths` 保存相邻图形页。该关联是保守布局启发式，尚不能覆盖所有跨页或扫描版论文。


### 后端与前端职责

- 后端是唯一真相源，负责：
  - 文件上传
  - job 状态
  - 分析执行
  - 产物持久化
  - 日志记录
  - 进程内异步任务调度
- 前端只负责：
  - 上传文件
  - 展示任务状态、阶段进度与实时日志
  - 渲染 Markdown
  - 下载 Markdown / JSON / parsed markdown

## 支持的输入与输出

### 输入

- `.txt`
- `.md`
- `.pdf`

### 输出

- Markdown 分析报告
- JSON 结构化结果
- PDF 结构化 Markdown 中间产物
- 按 job 存储的日志文件

研究型文献模式下，最终 Markdown 报告由后端统一渲染为固定目录结构，默认包含：

- `1. 基本信息`
- `2. 摘要式总结`
- `3. 研究问题`
- `4. 方法`
- `5. 实验与结果`
- `6. 图表分析`
- `7. 事实检查`
- `8. 评价`
- `9. 启发与参考价值`
- `10. 总结`
- `11. 领域结构化产物`：覆盖状态、故事架构、图组 Flow、细节证据矩阵和 Benchmark（无适用内容时明确标记）

最终 Markdown 仅保留报告正文，不输出 agent 中间协商、工具调用过程、链式推理文本或结构化解析预览。

`AnalysisResult.research_products` 与报告第 11 节使用同一份确定性组装结果。`verified` 只表示通过本项目的证据定位/QC 闸门，不代表专家正确性认证；缺失数据使用 `not_reported`，机制论文没有适用比较时使用 `not_applicable` 并说明原因。

## 环境配置

### 基础要求

- Python `3.12+`
- Node.js `18+`
- `uv`
- `npm`

### Python 依赖

安装后端依赖：

```bash
uv sync
```

### 前端依赖

首次安装前端依赖：

```bash
cd web
npm install
cd ..
```

### LLM 环境变量

系统以 Kimi API 为主要 LLM 提供方，走 OpenAI 兼容协议；同时保留任意 OpenAI 兼容端点的回退配置。应用启动时会自动加载项目根目录下的 `.env`，也兼容当前 shell 已导出的环境变量；如果两边同时存在，优先使用当前 shell 环境变量。

Kimi 配置（推荐，任一 `KIMI_*` 变量存在即生效）：

```bash
KIMI_API_KEY="your-kimi-api-key"          # 必填
KIMI_MODEL="kimi-k3"                       # 可选，默认 kimi-k3
KIMI_BASE_URL="https://api.moonshot.cn/v1" # 可选，默认 api.moonshot.cn
KIMI_TEMPERATURE="0.2"                     # 可选
KIMI_VISION_MODEL="moonshot-v1-32k-vision-preview" # 可选，启用真实图表视觉理解
```

两套 Kimi 账号体系的 endpoint 不同，按 key 来源选择：

- **开放平台按量 key**（platform.moonshot.cn / platform.moonshot.ai）：`KIMI_BASE_URL` 用 `https://api.moonshot.cn/v1` 或 `https://api.moonshot.ai/v1`，模型如 `kimi-k3`；视觉模型也可用。
- **Kimi Code 订阅 key**（kimi.com/code 控制台创建）：`KIMI_BASE_URL` 使用 `https://api.kimi.com/coding/v1`，模型按账号权限选择。当前项目已实测 `KIMI_MODEL=kimi-for-coding` 配合 `KIMI_VISION_MODEL=kimi-for-coding` 可通过 OpenAI 兼容接口读取图片。该端点未显式设置温度时自动使用 `temperature=1`。不同账号可用性应通过下方视觉自检确认，不需要伪装客户端身份。[官方图像输入配置说明](https://www.kimi.com/code/docs/en/third-party-tools/hermes.html)

- 不设置 `KIMI_VISION_MODEL` 时，图表语义回退为基于 caption 的保守模式。
- 视觉模型需选用当前端点和账号实际支持图像输入的型号；不要把开放平台模型名直接用于订阅端点。

OpenAI 兼容回退（未设置任何 `KIMI_*` 时生效，行为与之前版本一致）：

```bash
OPENAI_API_KEY="your-api-key"
OPENAI_BASE_URL="https://your-compatible-endpoint"
OPENAI_MODEL="your-model-name"
OPENAI_VISION_MODEL="your-vision-model"    # 可选
```

如果检测到已配置模型但缺少对应 API Key（`KIMI_API_KEY` 或 `OPENAI_API_KEY`），后端会在启动阶段直接报中文错误，而不是等到任务执行时才失败。

其他可选开关：

```bash
PAPER_ANALYSIS_PARALLEL_STAGES=1  # 正文理解与图表分析两个 LLM 阶段并行（默认串行）
VISION_REQUEST_TIMEOUT=240       # 可选；视觉 HTTP 请求超时秒数，默认 120；复杂多面板图可增加
```

如果你的运行环境需要代理，也请在当前 shell 中提前设置代理变量；`scripts/run.sh` 默认已把 `api.moonshot.cn` / `api.moonshot.ai` 加入 `NO_PROXY`。

### 应用配置文件

前后端主机和端口统一由：

- `config/app.json`

控制，默认示例：

```json
{
  "backend": {
    "host": "127.0.0.1",
    "port": 19198
  },
  "frontend": {
    "host": "127.0.0.1",
    "port": 11451
  }
}
```

修改端口时只需要调整这一个文件，并重启对应服务。

## 运行方式

### 1. 本地文件分析

运行本地分析主链路：

```bash
bash scripts/run.sh
```

默认输入输出：

- 输入：`input/sample_paper.txt`
- Markdown：`output/report.md`
- JSON：`output/report.json`

如果要分析 PDF：

```bash
INPUT_PATH=input/template.pdf \
OUTPUT_MARKDOWN_PATH=output/template_report.md \
OUTPUT_JSON_PATH=output/template_report.json \
bash scripts/run.sh
```

生成结果：

- `output/template_report.md`
- `output/template_report.json`
- `output/template_report.parsed.md`

### 2. 启动后端

```bash
bash scripts/run_api.sh
```

默认地址：

- `http://127.0.0.1:19198`

健康检查：

```bash
curl http://127.0.0.1:19198/health
```

### 3. 启动前端

```bash
bash scripts/run_web.sh
```

默认地址：

- `http://127.0.0.1:11451`

前端 dev server 使用固定端口策略；如果端口被占用，会直接报错，而不是自动切换端口。

## API 概览

前端当前只依赖以下接口：

- `POST /api/analysis/jobs`
- `GET /api/analysis/jobs/{job_id}`
- `GET /api/analysis/jobs/{job_id}/progress`
- `GET /api/analysis/jobs/{job_id}/report`
- `GET /api/analysis/jobs/{job_id}/artifact`

这些接口分别用于：
- 创建分析任务
- 查询任务状态
- 查询任务阶段进度和最新日志
- 获取 Markdown 报告
- 获取 Markdown / JSON / parsed markdown / log 等产物

## 运行提示

### 本地文件分析

- 如果默认输入不是你想分析的文件，使用 `INPUT_PATH` 指定源文件。
- 输出路径可通过 `OUTPUT_MARKDOWN_PATH` 和 `OUTPUT_JSON_PATH` 覆盖。
- PDF 解析和多 agent 分析可能耗时较长，属于正常现象。

### 后端与前端联调

- 先启动后端，再启动前端。
- `POST /api/analysis/jobs` 会在创建任务后立即返回；实际分析在后端进程内执行器线程中异步运行。
- 如果前端上传后显示 `Failed to fetch`，优先检查：
  - 后端是否已经启动
  - `config/app.json` 中的前后端端口是否正确
  - 当前端口是否被其他进程占用
- 前端会轮询后端 `job progress` 接口，展示文件接收、文档解析、多 Agent 分析、结果生成等阶段，并显示最新任务日志。

### 日志与问题排查

- API job 会把日志按时间戳写入对应任务目录。
- 如果一次分析失败，优先查看该 job 的日志文件。
- 本地 CLI 运行的标准输出仍会打印在当前终端。

## 输出规范

系统默认以简体中文输出说明性内容，包括：
- 章节标题
- 摘要与结论
- 优点、局限性、复现建议
- 图像实验结果分析

以下内容可保留原文：
- 论文标题
- 作者名、机构名、期刊/会议名
- 专业术语、模型名、方法名、数据集名、指标名、API 名称
- 直接引用原文的片段

## 测试

所有本地 Python 命令均通过 `bash scripts/run.sh` 执行，复用 uv 缓存、代理、遥测及工作区内的数据目录设置。不带参数仍执行原有文件分析入口。

运行单元测试：

```bash
bash scripts/run.sh python -m unittest discover -s tests/unit -p 'test_*.py'
```

运行集成测试：

```bash
bash scripts/run.sh python -m unittest discover -s tests/integration -p 'test_*.py'
```

### 真实视觉自检（显式调用模型）

```bash
KIMI_VISION_MODEL=kimi-for-coding bash scripts/run.sh python scripts/verify_vision.py
```

默认仅发送自动生成的合成柱状图；柱子标签和数值不出现在图注或提示词中。必须取得 `multimodal_llm` 结果并读出图内标记才返回成功，否则退出码非零。结果保存在 `output/vision-verification/semantic.json`；默认单元 / 集成测试不会调用真实模型。

核对实际论文的视觉解析（会发送选中的论文页面至所配置的模型服务）：

```bash
bash scripts/run.sh python scripts/verify_vision.py \
  --pdf ref_baseline/s41467-025-64293-2.pdf --limit 1 \
 --output output/paper-vision-verification
```

可增加 `--figure-id 'Figure 4'` 只核对特定图表。

通过该脚本只说明视觉接口返回了结构化结果，不代表论文理解准确率评测已完成。完整报告仍使用上文 `INPUT_PATH=... bash scripts/run.sh` 运行。

本次真实运行结果、简历能力边界及已知限制见 [项目能力审计](docs/project-capability-audit.md)。

## QC 质量控制

研究论文报告在渲染入口执行零模型调用的 QC，检查主张核验漏项、重复、未知 ID、证据定位及报告字段对应。正式总结只使用满足交付规则的主张，其余生成内容保存在 `qc_draft` 并标记待复核。任务执行状态与新增的 `quality.status` 独立：`completed` 不代表质量通过；旧结果的 `quality=null` 表示尚未检查。

可用 `bash scripts/run.sh python scripts/check_report_quality.py --source 原文.pdf --report 已有报告.json --output output/qc` 离线检查已有结果，不调用模型。接口变化、规则范围、原始草稿位置及已知限制见 [QC 使用说明](docs/quality-control.md)。


## 独立视觉模型与有界问答循环（2026-10-03）

配置模板见 [.env.example](.env.example)。已有 `KIMI_*` / `OPENAI_*` 行为保持兼容。
若保留 Kimi 做文本、使用百炼等 OpenAI 兼容服务读图，在本地 `.env` 增加：

```dotenv
VISION_API_KEY=
VISION_BASE_URL=https://YOUR_WORKSPACE_ID.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
VISION_MODEL=qwen3-vl-flash
VISION_TEMPERATURE=0.2
```

独立视觉配置启用后，`VISION_MODEL`、`VISION_API_KEY`、`VISION_BASE_URL` 必须同时提供；缺项直接报错，不会把文本模型密钥发送到视觉端点。`VISION_TEMPERATURE` 默认 0.2；`VISION_REQUEST_TIMEOUT` 仍以秒计。问答和全文报告统一复用该配置。将 `YOUR_WORKSPACE_ID` 替换为百炼控制台的业务空间 ID，API Key 与地域必须匹配；新加坡区将 `cn-beijing` 改为 `ap-southeast-1`。URL 不添加 `/chat/completions`。保留本地 `.env` 中原有 Kimi 订阅密钥，仅合并视觉配置；不要用空密钥模板覆盖已有文件。

2026-10-03 核对[官方接入文档](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)后，模板使用业务空间专属地址。默认选择低成本视觉模型 [qwen3-vl-flash](https://help.aliyun.com/zh/model-studio/qwen3-vl-flash)，复杂论文图表可改为 `qwen3-vl-plus` 对比效果。Kimi 负责文字分析与文本核验，Qwen 负责图片语义提取及问答原图复核。API 费用独立于 Kimi 订阅，不保证免费；按控制台额度及地域价格计费。此方案尚未通过本项目的 Qwen 真实调用和领域质量评测。

视觉缓存新增端点、模型及采样配置的指纹，避免同名模型跨供应商误用缓存；指纹不含密钥。问答审计记录视觉配置指纹及完整 Python 包代码指纹。旧审计可继续读取，新缓存与旧缓存分开。

若注册的是**千问AI平台 Token Plan**，使用套餐专属密钥和 `https://token-plan.maas.qianwenaiapi.com/compatible-mode/v1`，视觉模型改为 `qwen3.8-flash`。[官方套餐模型列表](https://platform.qianwenai.com/docs/token-plan/overview)与百炼按量模型列表不同。本项目真实预检中，Token Plan 请求 `qwen3-vl-flash` 返回 HTTP 404 `model_not_found`，改用 `qwen3.8-flash` 后合成视觉测试通过。模型、密钥、端点必须按所购服务成组配置。

Kimi + Qwen3.8-Flash 已完成五场景真实问答冒烟，接口可用，但细小标签提取和复核仍存在错误；详见 [Qwen 冒烟记录](docs/QWEN_SMOKE_2026-10-03.md)。

问答最多执行初轮加两轮补取。`evidence_gaps` 新增 `vision`：当真实视觉不可用且只缺视觉证据时，一轮后停止，保留已支持的正文/图注部分或拒答；若仍缺方法、对照等正文证据，则允许有界补取。后续调用失败只能保留最近一次成功核验结果，不能恢复已被冲突撤回的旧主张。

问答生产装配增加直接看图复核：文本 checker 通过的视觉主张，还需把实际页面图片交给视觉适配器再次核对。复核请求不携带先前 OCR 摘录或核验结论；只交付逐条支持且 ID、原句对应的主张。冲突反馈进入后续纠错，失败、漏项和预算耗尽时不发布对应视觉主张。每题最多两次复核调用，相同图片和主张复用题内结果；这些是逻辑调用预算，不包含供应商 SDK 的内部重试次数。

目标子图单独提取并参与缓存键；审计保存每轮 `visual_review`、图片 SHA-256 与调用次数，最终答案的 `visual_checks` 对应已交付视觉主张。`visual_status=succeeded` 仅表示提取成功。全文报告保留原有图表提取与 QC 流程，本次直接看图复核闸门仅适用于问答。

当前仍使用同一配置的视觉模型进行独立调用，因此不能视作独立专家或正确性保证。人工参考评估仍待完成；真实历史问题与改进后复验见 [冒烟记录](docs/QA_SMOKE_2026-10-03.md)。


正文理解与事实核验的检索工具现在绑定后端文档，只接收关键词、章节名及有上限的窗口参数，禁止模型回传或替换 `paper_text`。问答 checker 的工具仅能检索本轮有界证据视图，单次工具输出最多 4000 字符。旧工具类保留供已有调用兼容。

报告正文提示执行 12,000 字符总上限，并为方法、结果、实验设置分配较多空间；避免长摘要/引言挤掉关键章节。这是字符预算，不是精确 Token 计费。问答提示也移除了重复的完整规则文本。
