# 生物信息与表观遗传学文献图表问答：P0–P2 恢复断点

> 2026-10-03 更新：用户已提供 PDF 和配置并明确要求真实冒烟，四场景已执行。工程检查通过，但发现视觉 OCR/颜色错误进入正式答案；不能宣称领域质量通过。详见 [本次记录](QA_SMOKE_2026-10-03.md)。以下授权阻塞、未执行及旧 PDF 指纹均为 2026-09-28 历史断点状态。


记录日期：2026-09-28。用途：在额度耗尽或会话中断后，先读本文，再继续工作。本文记录实现状态，不把尚未完成的真实调用写成已验证成果。

**最新续做状态**：断点后的工程收尾已完成；96 项单元测试、5 项 API 集成测试、前端生产构建及 diff 空白检查通过。`docs/qa-engineering.md` 已创建，PLANS/README/evals 说明已同步。尚未完成的执行项只有第 6 节所述待具体数据发送授权的真实冒烟；未收到授权，不可通过替代命令执行。

## 1. 用户目标与不可变约束

在 paper_analysis 中增量完成单篇 PDF 图表问答的 P0–P2 工程闭环，独立于人工标注材料推进。

- 保留 CrewAI、既有全文报告和 `/api/analysis` API；问答无需先生成报告。
- 复用统一 LLM/视觉适配器、PDF parser 和既有事实核验/QC。
- 输入问题及可选图号/子图，返回中文答案、逐条定位、不确定性和 answered/partial/refused 状态。
- 初轮之后最多两轮文内证据补取/纠错；视觉失败不得冒充读图成功。
- 后端是唯一持久状态来源；前端只有当前 UI 状态及 URL 任务 ID。
- 不扩展外部检索、多论文综述、模型训练；不以离线回归或真实请求成功替代领域效果验证。
- 本地命令统一 `bash scripts/run.sh ...`。不直接 `uv run kickoff`。
- 工作区已有大量未提交的 QC、报告和文档改动，必须保留，不整体回滚、不覆盖。

## 2. 本轮整体方向

数据链路：上传 → PDF 指纹 → 持久任务 → 独立工作进程 → 结构缓存 → 定向证据/页面 → CrewAI 问答 → 独立事实核验 → 确定性交付闸门 → 每轮审计 → 最终答案 → 前端引用查看。

P0：主张自身引文定位、正文/图注/视觉区分、页面/子图约束；按方法/对照/统计/结果补取；停滞停止；技术失败保留先前部分答案，但新增冲突不得恢复被否定主张。

P1：后台提交、进度、取消、超时、显式重试、重启恢复；同步端点兼容；点击证据查看 PDF 页与原始正文 bbox。

P1/P2：PDF SHA256 + parser 代码/PyMuPDF 版本缓存；文件锁、原子写入、按需页面渲染；逐尝试/逐轮审计和批量候选运行。

## 3. 已实现代码及职责

以下路径相对仓库 `/home/lijy/workspace/paper_analysis`。

| 文件 | 当前职责/改动 |
| --- | --- |
| `src/paper_analysis/domain/qa.py` | 问题、主张、证据、回答、任务、逐轮和逐尝试审计的类型化协议；evidence_gaps、stop_reason、文档指纹、运行时间及运行代码指纹 |
| `runtime/pipelines/question_answer.py`（位于上述包内） | 独立问答流程；定向补取、最多两次 followup、停滞停止、错误降级、审计回调、目标页面集合校验 |
| `runtime/pipelines/qa_quality.py` | 每个引文与引用位置互相对应；checker 引文不能替代回答引文；视觉来源、子图及伪装来源约束 |
| `runtime/crews/research/question_answer.py` | CrewAI 问答 runner，经统一 LLM 适配器调用 |
| `runtime/crews/research/fact_check.py` | 保留既有核验；为问答的有界证据视图提供最多 20,000 字符的完整带 ID 摘录，避免沿用报告的 16,000 截断遗漏末尾证据 |
| `config/qa_prompt.txt` | 中文领域约束、来源区分、不执行论文中的指令、证据缺口分类 |
| `adapters/parser/pdf.py` | 新增兼容参数 render_assets，默认 True 保持报告行为；问答 False 只保留页面定位 |
| `adapters/parser/qa_cache.py` | 内容寻址解析缓存、校验清单、进程文件锁、原子写入、页面渲染/高亮、OnDemandFigureExtractor |
| `adapters/storage/qa_store.py` | 原子 JSON 与本地任务读写 |
| `adapters/llm/base.py`、`openai_compatible.py` | 不含凭据的模型审计元数据接口 |
| `services/question_answer_service.py` | 上传校验、任务准备、解析/问答执行、审计、答案发布保护、证据页面；默认生产工厂标记 real_call，测试注入默认 offline_test |
| `services/question_jobs.py` | 单主管队列、默认并发 2、执行上限 600 秒、子进程终止、尝试隔离、重启恢复；失效结果不发布 |
| `services/question_worker.py` | 工作进程入口；Linux 父进程死亡信号保护；调用 service，不包含领域逻辑 |
| `services/qa_evaluation.py` | 候选批量准备检查/真实运行；指纹不符或未绑定不调用；每批独立清单及最新清单；专家评分始终 not_evaluated |
| `api/routes/questions.py` | 新增后台任务、列表、状态、取消、重试、审计、页面；原同步端点经同一队列等待 |
| `api/app.py` | lifespan 启停问答主管；可注入离线测试主管 |
| `scripts/run_qa_batch.py` | 薄 CLI，默认仅准备检查；只有显式 --real 才允许调用模型 |
| `web/src/components/QuestionPanel.jsx` | 后台提交/轮询、恢复后端任务、取消重试、点击引用显示页/框、查看审计 |
| `web/src/api/client.js` | 新增队列、审计/页面 URL 等客户端接口；原报告接口保留 |
| `evals/qa_candidates.jsonl`、`qa_annotation_template.json`、`qa_README.md` | 16 条未标注候选：12 条待绑定题型 + 4 条本地 MoDorado 子图问题；不是金标准 |
| `evals/qa_smoke.jsonl` | 已准备 4 个真实冒烟场景：正文、Figure 4a、缺失 Figure 99a、关闭视觉后的降级 |

## 4. API 与存储约定

- `POST /api/qa/jobs`：multipart PDF/question/figure/panel/max_followups，返回 202。
- `GET /api/qa/jobs`、`GET /api/qa/jobs/{id}`：最近任务和执行阶段。
- `POST /api/qa/jobs/{id}/cancel`、`POST /api/qa/jobs/{id}/retry`。
- `POST /api/qa/questions`：兼容同步接口，等待同一个队列，超时 504。
- `GET /api/qa/questions/{id}`：仅完成任务发布答案。
- `GET /api/qa/questions/{id}/audit`：当前尝试审计；历史审计留在磁盘。
- `GET /api/qa/questions/{id}/pages/{page}?evidence_id=...`：真实 PDF 页 PNG，可高亮正文 bbox。

默认 `.data/questions/{id}/`：`source.pdf`、`request.json`、`job.json`、`parsed.json`、`audit-{attempt}.json`、`result-{attempt}.json`、`answer.json`。缓存位于 `.data/questions/cache/{sha256}/{parser_version}/`。

当前为 Linux 单 API 主管进程版本，不能启动多个 Uvicorn workers 竞争同一目录。任务和回答状态相互独立：completed 可以得到 refused；不表示论文结论正确。引用页码使用 PDF 物理页码（从 1 开始），视觉图注页和实际图像输入页可能不同。

## 5. 已执行验证与最后改动边界

- 全量单元测试最近一次：**96 项通过**（初次断点为 95，续做新增配置失败留痕回归后为 96）。
- API 集成最近一次：**5 项通过**（原报告 2、同步问答 1、新后台/证据页面 1、同步超时 1）。
- 前端 `npm --prefix web run build` 最近一次通过。
- 工程回归覆盖：伪造引文、checker 引文不能替代自身引文、错页视觉、统计证据补取、停滞停止、后续调用失败保留部分回答、新冲突不恢复旧主张、扫描/损坏 PDF、并发缓存/文件内容变化/版本变化/缓存损坏、任务取消/超时实际杀进程/迟到发布阻止、主管互斥、恢复与重试、证据高亮、批量指纹不符不调用。
- 原有视觉/跨页/子图/报告测试在全量中一并通过。
- 四个真实冒烟场景的**无模型准备检查通过**，结果在 `evals/runs/qa-engineering-preflight/manifest.json`；execution 全为 not_called。

初次断点时待复验的小改动（service.execute 拒绝非 running/旧 attempt、终止审计封存、迟到结果保护、明确 stop_reason、页面损坏错误、独立 run_id 清单）均已包含在续做后的 96 项全量回归中。另补齐批量工具的配置失败/主管启动失败记录和清理，配置失败不泄露供应商异常正文。

新增测试文件：`tests/unit/test_qa_engineering.py`、`tests/unit/test_qa_evaluation.py`、`tests/integration/test_qa_jobs_api.py`。已有问答测试位于 `test_question_answer.py`、`test_qa_api.py`。

沙箱内 asyncio 线程唤醒曾挂起，包括既有 TestClient 健康检查；离线测试改用获准的沙箱外执行后通过。沙箱外测试仍为 fake/合成 PDF，不调用模型。

## 6. 真实调用阻塞及授权状态（必须保留）

拟执行命令：

```bash
bash scripts/run.sh python scripts/run_qa_batch.py --manifest evals/qa_smoke.jsonl --output evals/runs/qa-engineering-smoke --real
```

该命令被自动审批拒绝，**未执行**。原因：虽然用户已要求完成真实冒烟，但自动审批要求明确确认具体 PDF 与外部模型目的地的数据发送。不得换命令、通过测试或间接执行绕过。

已通过仅本地读取配置确认：目的地主机 `api.kimi.com`，文本/视觉模型均 `kimi-for-coding`，不记录 API key。

拟发送材料：本地公开 MoDorado 论文 `ref_baseline/gkaf795.pdf` 的选定正文、图注、Figure 4 页面图像。SHA256：`f47a24c8b1717944ca1a7bef018778290c8a86851709e44a1ffa63db5df02e75`。

此前已向用户发送异步确认，选项为“授权这篇论文与该目的地的冒烟调用”或“本轮仅完成工程与离线验证”。**截至写入本文，没有收到明确授权答复**。用户本次“先写断点文档再继续”的要求不等于上述数据发送授权。恢复时先检查是否已有新答复；未授权时继续工程与离线验收，真实冒烟保持待确认。

没有新增真实问答结果，也没有专家效果评分；不要据此宣称答案正确率、幻觉降低或生物学可靠性。

## 7. 余下任务（按顺序恢复）

1. [x] 先保存本断点文档（本次用户明确要求）。
2. [x] 检查最后小改动，重跑全量单元、批量准备检查和 API 回归。
3. [x] 完成 `docs/qa-engineering.md` 工程验收文档及 README 对应说明。
4. [x] 更新 `PLANS.md` 顶部 P0–P2 清单及 `evals/qa_README.md`，区分工程完成与真实冒烟待授权。
5. [x] 批量配置失败/主管启动失败分别保存记录和释放资源；新增配置失败回归。
6. [ ] 若收到明确的数据发送授权，再运行四场景真实冒烟；检查审计、回答状态、视觉状态、指纹与工程门禁，修复真实链路问题并按需有限复验。没有授权则不执行。
7. [x] 最后代码检查与测试通过，本文及验收结果已更新；之后仅文档收尾。
8. [x] 工程结论：实现和离线验收完成，真实调用仍因第 6 节授权条件阻塞，不宣称 P0–P2 所有验证全部完成。

推荐恢复命令：

```bash
git status --short
bash scripts/run.sh python -m unittest discover -s tests/unit -p 'test_qa_engineering.py' -v
bash scripts/run.sh python -m unittest discover -s tests/unit -p 'test_qa_evaluation.py' -v
bash scripts/run.sh python -m unittest discover -s tests/integration -v
bash scripts/run.sh python scripts/run_qa_batch.py --manifest evals/qa_smoke.jsonl --output evals/runs/qa-engineering-preflight
git diff --check
```

`evals/runs/`、`.data/`、PDF 与模型配置为本地忽略产物；不要提交凭据或整篇论文。当前未创建提交或 PR，也没有用户要求创建。
