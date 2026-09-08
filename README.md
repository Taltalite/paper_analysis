# Paper Analysis

一个基于 CrewAI 的研究型文献分析系统，支持本地文件分析、FastAPI 后端服务和轻量 Web 前端。

系统面向的核心场景是：
- 读取 `txt` / `md` / `pdf`
- 解析论文结构与图表信息
- 生成简体中文为主的 Markdown / JSON 分析结果
- 通过后端 job 接口统一管理任务状态与产物

## 架构概览

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

最终 Markdown 仅保留报告正文，不输出 agent 中间协商、工具调用过程、链式推理文本或结构化解析预览。

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
