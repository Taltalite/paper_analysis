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

#### 通用文本分析

通用文本链路使用 2-agent 模式：

- `reader`
  提取可追溯的结构化信息
- `analyst`
  汇总分析结论并生成最终报告

#### 研究型文献分析

当前仓库的完整研究论文分析链路已经扩展为 6 个明确分工的 agent / role：

- `reader`
  负责重点章节阅读与事实性笔记提取
- `analyst`
  负责正文层研究问题、方法、结果、优缺点与复现建议总结
- `document_structuring`
  负责 PDF 元数据校正、章节归并、caption 与正文引用映射
- `figure_grounding`
  负责图片语义 grounding，整理局部图片路径、图类型、panel、visible text、axis 等基础视觉证据
- `figure_evidence_curator`
  负责把 caption、正文引用和 grounding 证据整理成统一 `FigureEvidence`
- `figure_analyst`
  负责基于证据对象输出图像结论与图文一致性检查

其中，前 2 个角色构成通用文本分析 base；后 4 个角色是研究型文献场景的增强层。

PDF 文献分析的当前执行顺序为：

1. 通过 parser 读取源文件。
2. 对 PDF 按阅读顺序提取 text/image blocks。
3. 使用规则生成粗结构草稿：
   标题、作者、摘要、章节、figure caption、正文引用关系。
4. 使用 `document-structuring agent` 做语义校正和结构归并。
5. 将校正后的高价值章节交给正文分析 agents。
6. 使用 `figure_grounding agent` 生成图片语义基础证据。
7. 使用 `figure_evidence_curator agent` 把 caption、正文引用和视觉证据整理成统一证据对象。
8. 使用 `figure_analyst agent` 基于证据对象分析图、表结论与图文一致性。
9. 输出最终 Markdown、JSON，以及 PDF 的结构化 Markdown 中间产物。

当前已经提供 `FigureSemanticExtractor` 抽象与 `NoopFigureSemanticExtractor` 回退实现。
这意味着图片链路已经具备独立语义证据层，但真正的 MCP 图片语义工具仍是下一步接入重点。

### 后端与前端职责

- 后端是唯一真相源，负责：
  - 文件上传
  - job 状态
  - 分析执行
  - 产物持久化
  - 日志记录
- 前端只负责：
  - 上传文件
  - 展示任务状态
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

当前已实现 `openai-compatible` 适配层，常用环境变量如下：

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://your-compatible-endpoint"
export OPENAI_MODEL="your-model-name"
```

如果你的运行环境需要代理，也请在当前 shell 中提前设置代理变量。

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

- `http://127.0.0.1:8010`

健康检查：

```bash
curl http://127.0.0.1:8010/health
```

### 3. 启动前端

```bash
bash scripts/run_web.sh
```

默认地址：

- `http://127.0.0.1:5173`

前端 dev server 使用固定端口策略；如果端口被占用，会直接报错，而不是自动切换端口。

## API 概览

前端当前只依赖以下接口：

- `POST /api/analysis/jobs`
- `GET /api/analysis/jobs/{job_id}`
- `GET /api/analysis/jobs/{job_id}/report`
- `GET /api/analysis/jobs/{job_id}/artifact`

这些接口分别用于：
- 创建分析任务
- 查询任务状态
- 获取 Markdown 报告
- 获取 Markdown / JSON / parsed markdown / log 等产物

## 运行提示

### 本地文件分析

- 如果默认输入不是你想分析的文件，使用 `INPUT_PATH` 指定源文件。
- 输出路径可通过 `OUTPUT_MARKDOWN_PATH` 和 `OUTPUT_JSON_PATH` 覆盖。
- PDF 解析和多 agent 分析可能耗时较长，属于正常现象。

### 后端与前端联调

- 先启动后端，再启动前端。
- 如果前端上传后显示 `Failed to fetch`，优先检查：
  - 后端是否已经启动
  - `config/app.json` 中的前后端端口是否正确
  - 当前端口是否被其他进程占用

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

运行单元测试：

```bash
UV_CACHE_DIR=.uv-cache XDG_CACHE_HOME=.cache uv run python -m unittest discover -s tests/unit -p 'test_*.py'
```

运行集成测试：

```bash
UV_CACHE_DIR=.uv-cache XDG_CACHE_HOME=.cache uv run python -m unittest discover -s tests/integration -p 'test_*.py'
```
