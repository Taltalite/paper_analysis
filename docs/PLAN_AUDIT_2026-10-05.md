# 项目改进计划审核与 smoke test（2026-10-05）

## 审核结论

**尚未完成全部计划，不能按整体交付验收。** 当前已实现策略/领域 schema、基础账本、部分 API 参数和领域报告骨架；已有功能回归通过。但 WP-02～WP-07 多项核心验收条件未满足，WP-08/09/10/11 仍有明显缺项。

审核基准：[项目改进计划](PROJECT_IMPROVEMENT_PLAN_2026-10-04.md)。审核对象为当前工作区（含已有未提交变更），不是只检查 Git 已提交版本。本次保留业务代码，只增加审核文档与本地复现产物。

## 工作包逐项判定

| 工作包 | 判定 | 已有成果与未完成项 |
| --- | --- | --- |
| WP-00 | 基线资料已建立，本次补齐复验 | 历史 baseline 记录环境/挂起；本次沙箱外完整单元/API 回归通过，纠正“无法验证”的环境边界 |
| WP-01 | 基础契约完成，完整验收未完成 | execution/research schema 已有；完整会话协议、接口样例、全部引用/空值/版本迁移测试尚不完整 |
| WP-02 | 部分完成，关键约束不满足 | 视觉有逐请求预留/usage；文本只在阶段外包一层，内部多请求/SDK 重试不受逐次治理；生产输出限制未贯通 |
| WP-03 | 部分完成 | 策略与结束时汇总持久化；每 attempt 新建账本，未跨重试累计；逐调用发送前/后落盘未实现，强杀可丢失用量 |
| WP-04 | 部分完成，泄漏未关闭 | 视觉错误已细分；问答 uncertainties 仍合并模型自由文本；新报告细节证据/benchmark 也存在未核验内容直接展示 |
| WP-05 | 骨架完成，领域目标未完成 | 新第 11 节和四类 schema 已有；故事线主要按 claim 顺序拼接、图组主要按出现顺序连接，缺少真正的问题/设计/论证抽取；实验条件字段维持默认；benchmark 缺生成要求与验证绑定 |
| WP-06 | 部分完成 | 档位控制部分轮数/选图；无报告有界补证据循环、核验预算预留、agent 迭代/原生推理参数贯通 |
| WP-07 | 部分完成 | 复用页面和目标 panel 提示/缓存；无可信 region 裁剪闭环；报告未装配问答同等的直接图像复核 |
| WP-08 | 未实现 | 无持久化 conversation/turn、指代澄清和跨 turn 预算 |
| WP-09 | 未实现主要目标 | 报告仍在线程池，缺可杀死子进程、取消/重试/重启恢复的完整主管机制 |
| WP-10 | 部分完成 | API 有新增策略字段；Web 无强度/预算控制、用量/领域专门视图及连续追问 |
| WP-11 | 部分完成 | 现有回归通过；完整故障矩阵、报告批测、CI 门禁、not_applicable 指标分母和预算父账本未齐 |

不计算虚假的“完成百分比”：schema 存在、测试通过和满足产品验收不是同一种完成程度。`PLANS.md` 顶部 WP-02～WP-07 的勾选应仅理解为基础实现记录，不能代表对应工作包全部验收通过。

## 关键发现（按修复优先级）

### F1 · P1：文本 budget / max_calls 不能约束实际底层调用，输出上限未贯通

位置：`runtime/pipelines/question_answer.py:296`、`runtime/pipelines/general_text.py:75`、`adapters/llm/openai_compatible.py:87`。

`_run_text_stage()` 只对整个 runner 预留并记录一次；一个 runner 内部的多次 LLM 请求不会重复检查账本。离线复现设置 `max_calls=1`，被包裹的模拟 runner 内部执行 3 次调用动作，仍返回成功，账本只记 1 次。该探针证明边界位置不正确，不声称本次真实模型已经超支。

`to_crewai_llm()` 仅传模型/凭据/温度，没有传策略的输出限制、重试上限或 deadline。当前已安装 CrewAI 原生 OpenAI SDK 默认重试为 2，实际任务账本无法覆盖这些尝试。视觉路径虽然支持 `max_output_tokens`，抽取与复核调用方没有传入，payload 只在显式参数不为 None 时写 `max_tokens`；因此“账本预留了输出”不代表请求真的限制了输出。

修复要求：计量下沉到每次实际请求；禁止/接管隐式重试；解析生效策略并传递输出/超时上限；用 mocked transport 而非仅 fake runner 验证请求次数。

### F2 · P1：正式问答的不确定性说明仍泄漏未核验断言

位置：`runtime/pipelines/question_answer.py:284`（以及第 110 行追加原视觉不确定性）。

返回内容直接拼接 `draft.uncertainties`。在 fake 模型中注入 `FAKE_LABEL_999`，答案可为 `answered`，该未核验标签仍进入最终 JSON 的 uncertainties。WP-04 要求的确定性原因模板/草稿隔离尚未实现。

修复要求：模型自由说明留审计草稿；正式说明用原因代码和模板，或把其中事实纳入逐条核验。覆盖 UI、下载与结果 API 的展示通道。

### F3 · P1：新增报告章节绕过原 QC 的正式交付边界

位置：`runtime/pipelines/research_paper_report.py:203`、`research_products.py:185`。

公开 `render()` 入口复现：QC 为 blocked、无获支持主张时，`UNSUPPORTED_CLAIM_999` 仍出现在“11.4 细节证据”，该行未标为未核验。传入不存在的 benchmark evidence ID 会被过滤成空列表，但 `InventedMethod / accuracy 99.9` 仍以 `available` 进入“11.5 Benchmark”。单纯检查 ID 是已知集合的子集会接受空集合，不能证明有依据。

修复要求：领域条目需要 claim/核验绑定；细节矩阵携带验证状态并过滤/隔离；benchmark 数值只在所需证据和验证完整时进入正式视图。加入 public renderer 回归，而不只测试组装函数存在字段。

### F4 · P1：重试与终止无法保持完整预算审计

位置：`services/question_answer_service.py:75`、`:83`、`:100`。

每次 execute 新建空 `BudgetLedger`，未读取以前 attempt 的已消耗额度。轮次回调只保存 rounds，执行 summary 到整个 pipeline 返回/异常时才生成；被主管强杀时 finally 无法保证执行，可能缺少已发送请求的记录。报告线程生命周期也不能提供强制中止保证。

修复要求：逻辑 job 父账本跨 attempt 累积；每次预留/发送/结算持久化；主管把中断时未结算记录标记 unknown；补齐报告进程主管后再验收强制终止。

### F5 · P2：新领域证据注册表遗漏 S1 等章节证据

位置：`runtime/pipelines/research_products.py:83`。

新注册表只收集正文 block 与 figure，没有合并 parser 的 `evidence_map.sections`。构造已被 QC 接受、引用 `S1` 的主张，领域 finding 仍标 verified，但 `evidence_ids` 被过滤成空列表。这破坏既有正文证据与新领域产物的对应。

修复要求：复用统一证据注册协议；保留章节定位/原始文本；获支持状态不能在引用被清空后继续保留。

### F6 · P2：供应商只返回部分 usage 时，记录丢失

位置：`runtime/budget.py:176` 附近。

当 usage 仅包含 input、无法计算 total 时，代码局部构造了带 reserved/unknown 的 usage，却没有赋给 `record.usage`。复现 `TokenUsage(input=50)` 后，记录为 unknown 但 usage 为 null，已知 input=50 也丢失。

修复要求：保留所有已知子项与未知总量；增加重复 settle 的幂等性和未知结算回执测试。

### F7 · P2：领域骨架和覆盖信息不能代替领域分析完成

位置：`runtime/pipelines/research_products.py:117`、`:156`、`:227`。

故事节点由 category/claim_id 的字符串规则映射，不能产生完整 problem/design 链路；边仅为清单/图表顺序。证据矩阵构造未填样本/条件/重复/对照。coverage 把已选章节直接列为 verified，把存在视觉观察的图列为 verified，未要求相应核验通过。报告 pipeline 仍单遍执行，没有新增图像直接复核。

修复要求：明确区分“有结构占位”“模型抽取”“证据定位”“语义核验”；按 WP-05/06/07 补真实生成契约及反例测试，保持出现顺序与论证关系分离。

## 本次执行验证

### 既有回归

| 验证 | 结果 |
| --- | --- |
| 沙箱内单元测试，90 秒上限 | 超时，exit 124；停在后台任务恢复用例附近 |
| 沙箱内 API 集成，45 秒上限 | 超时，exit 124；首个 TestClient health 请求 |
| 沙箱外同一单元集，120 秒上限 | **122 tests，OK，exit 0**；unittest 报告 1.797 秒 |
| 沙箱外同一 API 集成集，90 秒上限 | **6 tests，OK，exit 0**；unittest 报告 0.604 秒 |
| `bash scripts/run.sh npm --prefix web run build` | **通过，exit 0**；197 modules，Vite 1.39 秒 |

这两处挂起在沙箱外未复现，因此本次没有将其认定为业务代码失败；不能据此推导所有线程/生产运行环境都已验证。前端只做构建，没有执行浏览器交互自动化。

### 计划约束离线 smoke

命令：

```bash
bash scripts/run.sh env PYTHONPATH=src:tests/unit:. \
  python output/plan-audit-2026-10-05/smoke.py
```

共 9 项：2 项通过（正文问答 happy path、缺图拒答）；7 项未满足断言（自由文本泄漏、证据矩阵泄漏、benchmark 无引用、章节引用丢失、阶段内部调用不受限、文本输出上限缺失、部分 usage 丢失）。脚本是审计收集器，正常退出仅代表成功收集结果，不代表这些断言全通过。

这些失败不是专家标注依赖，也不是模型准确率问题，是可用合成数据和 fake 重现的工程缺口。

### 真实接口 smoke

使用已有 `.env` 配置，未更改密钥或端点；仅发送合成文字和合成柱状图，不发送论文。每个真实请求显式限制输出 1024 tokens、45 秒 timeout、无自动重试。该测试验证接口连通/输入能力，不替代完整 PDF agent loop 的真实验收。

| 模型 | 结果 | 实际 usage | 耗时 |
| --- | --- | --- | --- |
| Kimi `kimi-for-coding` | 通过：回答生物学重复 3、技术测量总数 6 | input 118 + output 103 = **221 tokens** | 3.281 秒 |
| Qwen `qwen3.8-flash` | 通过：从合成图读出 Alpha 37、Beta 83 | input 1279 + output 78 = **1357 tokens** | 4.083 秒 |

合计 **1578 tokens**；Qwen 返回 reasoning 63 为 output 内子项，不再次累加。不据此推算套餐货币费用。Kimi 首次测试脚本在请求发出前因 SDK 属性名 `client`/`_client` 差异出现 AttributeError，修正测试脚本后只补跑 Kimi，没有重复 Qwen；原始失败保留在 JSON，不归因于业务代码或模型服务。

Kimi 本次实际 usage 来自已安装 CrewAI LLM 的 `get_token_usage_summary()`，说明“生产账本未采集”不等于 SDK 完全无 usage；逐 HTTP attempt 的治理仍需另行实现。两次测试的输出限额由测试脚本显式设置，不能作为生产请求已透传策略的证据。详细记录见 `output/plan-audit-2026-10-05/live-smoke.json`。

## 修复与复验顺序

1. 先修 F1/F2/F3：实际调用控制和正式结果交付闸门，避免继续扩展未受控链路。
2. 修 F4/F5/F6：跨 attempt 预算、持久化、证据统一与 usage 完整性。
3. 完成 WP-05/06/07 的领域生成、报告循环和图像核验，补 F7 覆盖语义。
4. 实现 WP-08/09/10，再用 WP-11 全矩阵验收；人工标注仍仅用于领域效果评价。

修复后需同时重跑既有 128 项测试与本次反例，不以旧测试全绿代替计划验收。真实论文端到端冒烟建议在 F1 关闭后进行，避免当前文本内部预算盲区造成不可控开销。

## 产物

- [离线审核脚本](../output/plan-audit-2026-10-05/smoke.py)
- [离线断言结果](../output/plan-audit-2026-10-05/smoke.json)
- [报告泄漏复现](../output/plan-audit-2026-10-05/unverified-report.md)
- [真实 smoke 脚本](../output/plan-audit-2026-10-05/live_smoke.py)
- [真实 smoke 结果](../output/plan-audit-2026-10-05/live-smoke.json)
- [单元复验日志](../output/plan-audit-2026-10-05/unit-unrestricted.log)
- [API 复验日志](../output/plan-audit-2026-10-05/api-unrestricted.log)

`output/` 属本地运行产物，可能被 Git 忽略；本报告保留核心结论，提交/交接时若需共享复现材料，应显式选择脱敏后的产物，不批量加入用户原始文献或缓存。
