# Paper Analysis

基于 CrewAI 的研究论文分析应用，支持 PDF 上传、证据问答、结构化报告、任务管理和 Markdown 下载。面向分子生物学、生物信息学与表观遗传学场景，以简体中文输出说明，保留论文原文、专业术语和可追溯引用。

当前版本提供可运行的 Linux 本地单主管服务。模块按领域、适配器、运行时和应用服务分层，后端负责全部任务状态与产物。共享部署前仍需完成任务访问隔离、容量与恢复验收。

## 功能

- 读取 `.txt`、`.md`、`.pdf`，解析正文、章节、图注及 PDF 源位置。
- 对单篇论文进行正文、数值和图表问答，返回主张、证据、物理页码与子图定位；支持最多两轮补取和同文档连续追问。
- 生成 Markdown / JSON 研究报告，包含故事架构、图组论证、证据矩阵和 Benchmark；无法支持的内容保留待核验标记。
- 后台报告与问答任务支持查询、取消、超时、重试和重启恢复；任务状态及产物由后端保存。
- 分别配置文本和视觉模型，记录每次请求及累计用量；视觉主张需要直接原图复核。
- 提供固定论文参考集、独立评分及检索、视觉、回答等错误分类。

## 快速开始

### 环境与依赖

使用 Linux、Python 3.12 或 3.13、Node.js 20 及 npm，并安装 `uv`。Python 与前端依赖分别由 `uv.lock` 和 `web/package-lock.json` 固定。

从仓库根目录执行：

```bash
UV_FROZEN=1 bash scripts/run.sh uv sync --frozen
bash scripts/run.sh npm --prefix web ci

# 首次配置；-n 保留已经存在的本地配置
bash scripts/run.sh cp -n .env.example .env
bash scripts/run.sh cp -n config/app.example.json config/app.json
```

编辑本地 `.env`，填写 `KIMI_API_KEY` 与 `VISION_API_KEY`。这两项密钥分别属于文本和视觉服务；模板不含密钥。模板采用已通过合成 smoke 的配置：

| 用途 | 型号与参数 | 环境变量 |
|---|---|---|
| 文字理解、问答与事实核验 | `k3-256k`，`reasoning_effort=high`，温度 1 | `KIMI_*` |
| 图像提取与原图复核 | `qwen3.8-flash`，温度 0.9，单次输出上限 16,384 | `VISION_*` |

型号、端点和密钥须与账号对应。模板使用 Kimi Code 与千问 Token Plan 端点；也可成组替换为其他受支持的 OpenAI 兼容配置，变量见 [.env.example](.env.example)。接口连通和合成 smoke 通过不代表论文回答准确率已提升。

应用自动加载根目录 `.env`，已导出的 shell 环境变量优先。修改模型配置后重启后端；旧任务的策略和账本继续保留。

### 启动服务

在两个终端分别运行：

```bash
# 后端
bash scripts/run_api.sh

# 前端
bash scripts/run.sh bash scripts/run_web.sh
```

示例配置只绑定回环地址：前端 `http://127.0.0.1:11451`，后端 `http://127.0.0.1:19198`，健康检查 `/health`，交互 API 文档 `/docs`。

主机、端口和 CORS 来源由本地 `config/app.json` 决定；可通过 `PAPER_ANALYSIS_CONFIG_PATH` 指定另一份配置，前后端须使用同一文件。实际地址以该配置为准，端口占用时前端不会自动换端口。

启动脚本统一配置 uv 缓存、遥测和代理。若本机没有 `127.0.0.1:7890` 代理，在上述运行命令前加 `PAPER_ANALYSIS_DISABLE_PROXY=1`；有代理时按实际环境配置。

### 命令行分析

```bash
# 内置文本示例，结果保存在 output/report.md 与 output/report.json
bash scripts/run.sh

# 将源 PDF 放在本地 input/，不随 Git 同步
INPUT_PATH=input/paper.pdf \
OUTPUT_MARKDOWN_PATH=output/paper-report.md \
OUTPUT_JSON_PATH=output/paper-report.json \
bash scripts/run.sh
```

PDF 模式还会输出结构化 Markdown 解析产物。真实分析会把所选正文及图像发送至已配置的模型端点。

## 执行额度与质量

新执行采用 `execution-v1` / `policy-v2`：

| 档位 | 累计 token 预算 | 单次输出上限 | 请求数上限 | 执行时限 |
|---|---:|---:|---:|---:|
| light | 100,000 | 16,384 | 8 | 180 秒 |
| standard | 300,000 | 65,536 | 16 | 420 秒 |
| deep | 600,000 | 98,304 | 32 | 720 秒 |

额度按单次单篇执行；固定论文批测中，每篇四题共享一份账本，下一篇重新建立账本。会话各轮共享累计用量，任务重试不清零。显式额度受服务端上限约束，原生推理强度与执行档位分别控制。视觉请求默认最多 16,384，且受任务输出上限裁剪。

请求发送前预留额度，完整供应商 usage 按实际消费结算，未知消费保守记账；额度不是精确货币费用。HTTP/SDK 自动重试为 0，工具交互和格式修复仍逐请求计量。任务时限与 `TEXT_REQUEST_TIMEOUT` / `VISION_REQUEST_TIMEOUT` 分别生效。

`completed` 表示执行与保存完成，`quality.status` 表示交付规则检查结果。正文、图注和直接视觉证据分别记录；未成功读取或复核目标图时不发布相应视觉主张。模型核验与 QC 不能替代独立正确性评价。报告与问答分别使用 `analysis-v2`、`qa-v2`，输入输出类型和验证规则由后端 Pydantic schema 定义。

## API

| 能力 | 接口 |
|---|---|
| 健康 | `GET /health` |
| 报告创建 | `POST /api/analysis/jobs` |
| 报告详情、进度及产物 | `GET /api/analysis/jobs/{id}` 及 `/progress`、`/report`、`/artifact` |
| 报告取消与重试 | `POST /api/analysis/jobs/{id}/cancel`、`/retry` |
| 问答创建与列表 | `POST /api/qa/jobs`、`GET /api/qa/jobs` |
| 问答状态、取消及重试 | `/api/qa/jobs/{id}` 及 `/cancel`、`/retry` |
| 最终回答、审计与证据页 | `GET /api/qa/questions/{id}` 及 `/audit`、`/pages/{page}` |
| 连续问答 | `POST /api/qa/questions/{id}/conversation`、`GET /api/qa/conversations/{id}`、`POST /api/qa/conversations/{id}/turns` |

上传使用 multipart，PDF 上限 30 MB。问题可指定 `figure`、`panel` 和 `max_followups`。异步创建返回 202；兼容同步接口 `POST /api/qa/questions` 经同一队列等待结果。具体输入、输出和状态以运行中的 OpenAPI 为准。

## 代码与数据布局

```text
src/paper_analysis/
  domain/       类型、schema 与执行策略
  adapters/     LLM、解析、检索和存储接口
  runtime/      CrewAI 流程、证据与交付闸门
  services/     应用编排、任务主管、会话和评价
  api/          FastAPI 薄路由
web/            React/Vite 界面
scripts/        统一启动、模型验证和评分入口
tests/          离线单元与 API 集成
config/         公开示例与本地配置
evals/          固定参考、评分摘要和评价说明
```

后端是任务和产物的唯一状态来源；前端只保存当前 UI 状态。业务任务保存在本地 `.data/`，输出保存在 `output/`，源论文保存在 `input/` 或 `ref_baseline/`。这些目录的私有材料不随仓库同步，部署迁移时需单独备份任务和文件。

## 验证与评测

默认测试使用 mock/fake 和合成 PDF，不需要真实 API Key，不调用外部模型：

```bash
bash scripts/run.sh python -m unittest discover -s tests/unit -q
bash scripts/run.sh python -m unittest discover -s tests/integration -q
bash scripts/run.sh npm --prefix web run build
```

API 测试隔离报告和问答的仓库、主管及锁，可与本地服务同时运行。已通过 163 项单元、6 项 API 集成和前端生产构建；浏览器交互未计入本轮验收。CI 配置了这些离线检查与 Playwright 浏览器测试，本地浏览器测试可执行：

```bash
bash scripts/run.sh web/node_modules/.bin/playwright install chromium
bash scripts/run.sh web/node_modules/.bin/playwright test --config web/playwright.config.js
```

需要确认模型配置时，显式运行最多两次合成请求：

```bash
bash scripts/run.sh python -m scripts.smoke_models \
  --configured-limits --output output/model-smoke-new
```

每次使用新目录。此命令会产生真实模型用量，默认测试与 CI 不执行。

固定 10 篇 / 40 题的参考状态为 `ai_provisional`，由独立阅读标注建立，Kimi/Qwen 只作为被测模型，不接收参考答案。数据身份、每项指标分母和评分命令见 [评价入口](evals/README.md)、[参考集](evals/datasets/paper_qa_v1/README.md) 与 [基线结果](evals/baselines/paper_qa_v1_2026-10-12/README.md)。源 PDF、原始模型回答和本机运行清单需在本地保留，仓库只提供参考定义与评分摘要。旧配置基线不能代替当前模型配置的新评测。

## 部署与数据管理

报告和问答使用 Linux 工作子进程，当前仅支持一个 API 主管进程，勿设置多个 Uvicorn workers。示例配置适合本机使用。前端本地入口是 Vite 开发服务；静态发布需要托管构建产物并配置 API 访问地址，地址改变后须重新构建。

共享部署前需完成身份与任务归属校验、队列和存储配额、诊断脱敏、保留期、备份恢复及真实容量验收。固定旧配置基线已发现状态、执行诊断、核验误杀和视觉证据传递缺口，当前适合本地质量内测；应先修正这些问题，再比较新模型并验证新的论文留出集。

`.gitignore` 保留源码、应用 agent/prompt、测试、锁文件、CI、公开模板、README 和正式评价定义；排除 `.env`、本机配置、上传论文、运行数据、归档、`docs/` 说明与实验记录，以及 `PLAN.md` / `PLANS.md` / `AGENTS.md` 等本地 agent 工作文件。运行、构建和测试不依赖这些本地文档，交互 API 文档由 FastAPI 自动生成。
