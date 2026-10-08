# 计划审核缺口修复与验收记录

本轮延续 `PLAN_AUDIT_2026-10-05.md`，增量修改现有 CrewAI 项目，保留原有未提交工作。人工标注不是工程开发的前置条件；专家正确性状态仍为 `not_evaluated`。

## 修复映射

| 审核项 | 本轮实现与验证 |
| --- | --- |
| F1 请求边界预算 | CrewAI 原生 SDK 同步/异步 HTTP hooks 在实际请求前预留，覆盖工具与格式修复的后续请求；强制输出上限，禁用 SDK 隐式重试。mocked transport 验证上限后第二次网络发送数为 0。 |
| F2 不确定性泄漏 | 模型 uncertainties 改为确定性提醒；视觉观察/理由保留审计及内部纠错，不作为正式回答的新增事实。 |
| F3 报告领域交付 | 证据矩阵只包含已核验且引用有效的主张。benchmark 要求 accepted claim、有效引用和原始数值/方法/指标文本绑定；不排名，不将未知数值补成 0。 |
| F4 账本与生命周期 | 每次预留、发送、结算原子落盘；跨 attempt、会话与顺序批次累计；中断用量保留未知。报告改为子进程，主管处理取消、超时、重启恢复和 attempt/文档指纹发布绑定。 |
| F5 章节引用 | registry 注册原始章节 S 系列引用，正式领域产物可回指原始章节。 |
| F6 部分 usage | 保留已知输入/输出子项，未知总量保守预留；重复结算幂等；cached/reasoning 作为子项不重复相加。 |
| F7 领域闭环 | story_role、实验条件、已核验关系构建故事与图表 flow；不以图号顺序推断论证。读过与核验过分别计数。报告支持最多两轮定向章节补取和直接看图复核。 |

原生 reasoning effort 能力声明为 unsupported；分析强度由系统迭代、选择范围、复核与输出额度控制，不暗中给供应商发送未知参数。

## 新增贯通能力

- 后端持久化 conversation、document_sha256、parent_turn_id 与共享预算；会话创建及追问/重试加锁；已有图号可以辅助解析“该图”等指代，无法唯一确定则要求明确对象。旧答案不是原文证据。
- 报告 worker 单独写 attempt 产物，主管验证绑定后发布；取消/超时回收进程组，重启时封存中断账本。API 进程不构建模型，启动即恢复报告队列。
- Web 显示策略、已知/未知用量、停止原因、领域产物，提供报告取消/重试和连续追问；URL 仅保留任务 ID，业务结果重新读取后端。
- QA 批次共享 token/call 额度；工程检查区分 false、not_applicable 和未执行，通过率分母排除后两种；真实执行失败时 CLI 非零退出。
- `.github/workflows/engineering.yml` 运行无供应商密钥的 Python 回归、前端构建和 Chromium 交互；模型 smoke 为独立显式命令。

## 本轮验证

| 检查 | 结果 |
| --- | --- |
| 单元回归 | 137 项通过，包含真实本地子进程取消/超时/重启/迟到产物测试 |
| API 集成 | 6 项通过，含真实 PDF parser、fake 视觉纠错、会话恢复与追问 |
| 浏览器交互 | 2 项通过：报告上传策略/取消/重试/刷新；追问 JSON/无重复上传/未知用量 |
| 前端生产构建 | 通过 |
| Kimi 合成文字 | 通过，3 个生物学重复与 6 次测量 |
| Qwen 合成图片 | 通过，识别 Alpha/Beta 与 37/83 |
| 真实调用总量 | 2 次，输入 1,389、输出 211、合计 1,600 tokens；reasoning 166 为输出子项 |
| 真实 smoke 预算 | 共享 8,000 tokens、2 次请求、单次输出上限 1,024、120 秒 |

复现命令（所有本地执行统一经过 run.sh）：

```bash
bash scripts/run.sh python -m unittest discover -s tests/unit -q
bash scripts/run.sh python -m unittest discover -s tests/integration -q
bash scripts/run.sh npm --prefix web ci
bash scripts/run.sh npm --prefix web run build
bash scripts/run.sh web/node_modules/.bin/playwright install --with-deps chromium
bash scripts/run.sh web/node_modules/.bin/playwright test --config web/playwright.config.js
# 仅显式需要真实接口时运行，输出目录必须为新目录：
bash scripts/run.sh python -m scripts.smoke_models --output output/new-model-smoke
```

本机 Chromium 最初因缺少 libnspr4/libnss3/libasound 无法启动。仅下载 deb 至 `/tmp/paper-analysis-browser-libs` 解包，以局部 `LD_LIBRARY_PATH` 完成浏览器验证，未修改系统安装。CI 使用 Playwright 的标准依赖安装。无代理环境可设置 `PAPER_ANALYSIS_DISABLE_PROXY=1`；本机原代理行为保持。

证据保存在 `output/plan-fixes-2026-10-05/`。历史 audit 输出没有覆盖；历史探针中的 stage fake 不模拟真实 SDK HTTP 边界，对应预算回归现在使用真实 SDK 与 mocked HTTP transport。

## 验收边界与后续入口

本轮补齐的是审核指出的核心工程缺口，并不宣称原计划的完整场景矩阵已经全部验收：

- 本次真实 smoke 只验证适配器与计量，没有重新跑完整真实论文的报告、所有目标子图和连续问答；API/浏览器闭环使用 fake 模型。后续应按原计划 11.1 固定论文场景补做有预算的真实回归。
- 图表 flow 当前以 figure 为节点；未知关系留空，尚未实现通用的精确 panel 自动裁剪与跨 panel 关系提取。图像核验仍用同一配置模型的独立请求，不等于独立专家。
- 报告补取当前选择未读章节；无新章节时停止，不无限循环。超出核验覆盖或预算的事实不交付。
- token 输入及图像消费仍为估算预留；供应商实际用量可能超估，随后按实际结算并阻止进一步调用。费用未计算。
- 当前 supervisor 基于 Linux 进程组及文件锁，适用于本地单 API 进程；没有引入分布式队列。
- CI 工作流已加入，云端 CI 未运行；本地等价命令已通过。领域准确率、幻觉降低比例、专家评分均未评估。

接续工作应以这份记录的真实验证范围为准，不将旧日期的能力说明或全绿单元测试等同于完整科研质量验收。
