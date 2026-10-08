# 项目改进实施进度（2026-10-04）

本次按 `docs/PROJECT_IMPROVEMENT_PLAN_2026-10-04.md` 的依赖顺序完成第一批工程改进，保留 CrewAI、既有 parser/adapter、API 和 Web 入口，并保留工作区已有未提交修改。

## 已落地能力

- `domain/execution.py`：执行强度、服务端上限、配置指纹、模型能力、TokenUsage、CallRecord、ExecutionSummary、CoverageReport。
- `runtime/budget.py`：线程安全请求前预留、发送后结算、未知用量保守扣留、重试/缓存命中和 deadline 检查。
- `domain/research.py` 与 `runtime/pipelines/research_products.py`：故事架构、图组 Flow、证据矩阵、Benchmark 和覆盖报告；正式报告第 11 节与 JSON 使用同一对象。
- LLM / 视觉适配：OpenAI-compatible 视觉请求支持输出上限、有限重试、供应商 usage 解析和独立 endpoint 审计；问答视觉复核细分失败原因。
- 任务持久化：分析和问答保存 requested/effective policy、配置指纹、execution summary 和 stop reason。
- 策略接入：`light`、`standard`、`deep` 控制问答补取、选图和视觉复核；报告的文本理解、图表分析和事实检查共享报告级账本。

## 定向验证

以下命令均通过 `bash scripts/run.sh` 执行，未进行真实模型调用：

| 命令 | 结果 |
| --- | --- |
| `python -m unittest tests.unit.test_execution_contracts tests.unit.test_budget tests.unit.test_research_products -v` | 9 项通过 |
| 分层执行全部不触发 `asyncio.to_thread` 挂起的单元模块 | 109 项通过 |
| `env PYTHONPATH=tests/unit python -m unittest test_visual_review test_independent_vision test_multimodal_contract test_pdf_parser test_schemas test_analysis_service -v` | 22 项通过 |
| 3 个 PDF / 缓存 /问答持久化定向测试 | 3 项通过 |
| `timeout 60s python -m unittest discover -s tests/integration -v` | 124；首个 `TestClient` health 用例无响应，环境问题待复验 |
| `npm --prefix web run build` | 通过 |

## 已知边界

1. 当前沙箱中，`asyncio.to_thread` 对稍有耗时的同步函数无法可靠唤回事件循环；因此保留同步问答入口的主线程 PDF 解析，并让生产后台问答使用独立子进程。依赖该环境行为的 `QuestionJobs` fake worker 集成测试仍不能作为本次通过证据。
2. FastAPI `TestClient` 集成测试在当前沙箱的首个请求处无响应；使用最小 FastAPI 应用也能复现，暂不能据此判断路由业务失败。应用导入、路由类型检查和前述服务级测试已完成；完整 API 集成需在正常 ASGI/TestClient 环境复验。
3. CrewAI 原生阶段目前没有逐 HTTP 暴露 usage；报告中的该类调用会记录为 `unknown` 并按预留额保守计入，实际供应商 usage 只有 OpenAI-compatible 视觉适配器可直接结算。
4. 用户连续追问会话、跨 turn 预算、报告任务的可杀死子进程 supervisor、前端策略/用量/故事视图和完整评估门禁尚未实现。
5. 没有新增真实 Kimi/Qwen 请求，也没有专家标注或领域准确率结论。
