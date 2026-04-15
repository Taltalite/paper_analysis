# Paper Analysis

本仓库已经从一个小型 CrewAI Demo，逐步演进为一个最小可运行的研究型文献分析系统。

当前状态：已完成 Phase 3，并完成面向用户输出的中文规范化改造。

- CrewAI 仍然是分析运行时。
- 支持纯文本与 PDF 输入。
- 后端负责任务状态与分析产物，是唯一真相源。
- 前端是一个轻量 React/Vite 页面，只负责上传、轮询、展示和下载。
- 最终 markdown 报告、前端文案、运行说明和默认输出模板，均以简体中文为主要说明性语言。

## 架构概览

- `src/paper_analysis/domain/`
  枚举、领域模型、输入输出 schema
- `src/paper_analysis/adapters/`
  LLM、parser、storage 适配层
- `src/paper_analysis/runtime/`
  CrewAI runtime、可复用 2-agent runner、分析 pipeline
- `src/paper_analysis/services/`
  分析编排、artifact 持久化、job 生命周期管理
- `src/paper_analysis/api/`
  FastAPI 应用、依赖注入与路由
- `web/`
  React/Vite 前端页面

## 支持的输入类型

- `.txt`
- `.md`
- `.pdf`

## 运行时分析链路

当前可复用基座仍然是 2-agent 模式：

- `reader`
  从原文中提取可追溯的结构化要点
- `analyst`
  将要点整理为最终结构化分析结果

在研究型文献分析场景下，后端 pipeline 会执行：

1. 通过 parser 抽象解析源文件。
2. 抽取摘要、引言、方法、实验设置、结果、结论、图示等结构。
3. 将 token 重点集中在高价值章节，而不是反复发送全文。
4. 使用 CrewAI 2-agent runtime 完成重点分析。
5. 持久化最终 markdown、JSON 与 PDF 结构化 markdown 中间产物。

## API 接口

前端只依赖以下 4 个后端接口：

- `POST /api/analysis/jobs`
- `GET /api/analysis/jobs/{job_id}`
- `GET /api/analysis/jobs/{job_id}/report`
- `GET /api/analysis/jobs/{job_id}/artifact`

后端统一负责：

- job 状态
- 上传源文件
- markdown 报告
- JSON 结果
- PDF 结构化 markdown 中间产物

## 运行配置

运行端口与主机地址已统一收口到：

- `config/app.json`

默认配置如下：

```json
{
  "backend": {
    "host": "127.0.0.1",
    "port": 8010
  },
  "frontend": {
    "host": "127.0.0.1",
    "port": 5173
  }
}
```

如果需要调整前后端端口，只修改这一处配置并重启对应服务即可。

## 启动方式

### 1. 本地文件分析链路

不要直接运行 `uv run kickoff`。

请使用：

```bash
bash scripts/codex_run.sh
```

默认输入输出：

- 输入：`input/sample_paper.txt`
- Markdown：`output/report.md`
- JSON：`output/report.json`

### 2. PDF 示例

运行仓库内置 PDF 示例：

```bash
INPUT_PATH=input/template.pdf \
OUTPUT_MARKDOWN_PATH=output/template_report.md \
OUTPUT_JSON_PATH=output/template_report.json \
bash scripts/codex_run.sh
```

会生成：

- `output/template_report.md`
- `output/template_report.json`
- `output/template_report.parsed.md`

### 3. 启动后端 API

```bash
bash scripts/codex_run_api.sh
```

默认监听地址：

- `http://127.0.0.1:8010`

健康检查：

```bash
curl http://127.0.0.1:8010/health
```

### 4. 启动前端

首次安装依赖：

```bash
cd web
npm install
```

启动前端：

```bash
cd ..
bash scripts/codex_run_web.sh
```

默认地址：

- `http://127.0.0.1:5173`

当前前端 dev server 使用 `strictPort`。如果端口被占用，会直接报错退出，不会偷偷切换端口。

前端通过 `config/app.json` 自动读取后端地址，不需要再去改前端源码里的 API URL。

## 前端页面范围

当前前端故意保持最小化，只包含：

- 上传 PDF / TXT / MD
- 提交分析任务
- 轮询并显示任务状态
- 在线展示 markdown 报告
- 下载 markdown
- 下载 JSON
- 在 PDF 场景下下载结构化 markdown 中间产物

前端不持久化业务状态，不作为状态真相源。

## LLM 配置

LLM provider 差异被封装在：

- `src/paper_analysis/adapters/llm/`

当前已实现：

- openai-compatible adapter

常用环境变量：

- `OPENAI_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`

如果未设置，CrewAI 仍会按其默认环境解析逻辑工作。

## 输出语言规范

系统当前默认遵循以下规范：

- 最终说明性内容以简体中文输出
- 论文标题、作者名、机构名、期刊/会议名保留原文
- 专业术语、模型名、方法名、指标名、数据集名、API 名称等在必要时保留原文
- 重要术语首次出现时，优先采用“中文解释（原文术语）”格式
- 不使用整段英文分析替代中文说明

## 测试

运行单元测试：

```bash
UV_CACHE_DIR=.uv-cache XDG_CACHE_HOME=.cache uv run python -m unittest discover -s tests/unit -p 'test_*.py'
```

运行集成测试：

```bash
UV_CACHE_DIR=.uv-cache XDG_CACHE_HOME=.cache uv run python -m unittest discover -s tests/integration -p 'test_*.py'
```

当前覆盖范围包括：

- schema 默认行为
- parser contract
- LLM adapter contract
- analysis service orchestration
- pipeline happy path
- FastAPI health route
- FastAPI job 创建、完成、报告读取与 artifact 读取

## 输出产物

纯文本输入：

- markdown 报告
- JSON 结果

PDF 输入：

- 结构化 markdown 中间产物
- 研究型文献 markdown 分析报告
- 结构化 JSON 结果

## 当前说明

- `api/routes/analysis.py` 暴露稳定的 job API
- `services/job_service.py` 负责上传保存、状态迁移、分析执行与产物读取
- `adapters/storage/job_store.py` 当前使用本地文件型 job store
- `web/` 保持薄层，不感知 CrewAI 内部细节
- Phase 1 和 Phase 2 的本地文件直跑链路仍然保留兼容
