# 固定 10 篇论文的问答评价

`reference.json` 与 [REFERENCE.md](REFERENCE.md) 保存 40 道固定问题、67 条必需参考主张和 56 项证据（44 段原文定位片段、12 个视觉区域）。每篇包含 2 道正文/数值题、1 道直接读图题和 1 道不存在图号题。最后一类是拒答检查，不代表真实业务问题分布，必须单列。

参考状态为 `ai_provisional`：用户明确授权使用本次 Codex 会话独立阅读形成的答案作为暂定 ground truth。问题、主张及证据全部由本会话助手直接阅读 PDF 正文与实际图像完成，不调用项目的 Kimi/Qwen 进行标注。Kimi 文本 + Qwen 视觉只在被测系统运行时生成预测。未经第二位独立专家仲裁；该状态不改写现有人工标注文件的状态。模型身份以客户端选择为准。

页码使用 PDF 物理页码，bbox 使用左上原点的 PDF 点坐标。正文引文是短定位锚点，其所在段落提供完整上下文；视觉证据记录直接观察，图注不能替代。引用不依赖运行时 `p*_b*` 或 `S*` 编号。原 PDF 及渲染图保留在本地，不纳入 Git。

当前评分采用 v1.1。运行前冻结的 v1.0 已原样保存；原文复核纠正 RARE-02 的数据集范围和专家人数，固定问题及被测输入不变，详见 [参考修订记录](CHANGELOG.md)。

全部 40 题真实基线及独立评价已完成，见 [结果、错误占比和实际用量](../../baselines/paper_qa_v1_2026-10-12/README.md)。复跑应另建输出目录；已有评价文件不应由空模板覆盖。

## 运行与评分

所有命令从仓库根目录执行。

```bash
# 校验文件指纹、页码、坐标和引文，生成只含问题/PDF绑定的被测清单
bash scripts/run.sh python scripts/score_qa_baseline.py --validate \
  --prepare-candidates evals/datasets/paper_qa_v1/candidates.jsonl

# 真实生产问答链路；每篇论文重新建立 standard 额度账本
PAPER_ANALYSIS_DISABLE_PROXY=1 bash scripts/run.sh python scripts/run_paper_baseline.py \
  --output evals/runs/paper_qa_v1_2026-10-12_standard --real --max-followups 0

# 每次复跑使用新的输出目录；模板只是工作表，未填写不能作为完成评价
bash scripts/run.sh python scripts/score_qa_baseline.py \
  --run evals/runs/paper_qa_v1_2026-10-12_standard/baseline_manifest.json \
  --write-review-template evals/runs/paper_qa_v1_2026-10-12_standard/reviews-template.json

# 独立阅读原文、目标图、最终输出及审计并填写工作表后，计算评分
bash scripts/run.sh python scripts/score_qa_baseline.py \
  --run evals/runs/paper_qa_v1_2026-10-12_standard/baseline_manifest.json \
  --review evals/runs/paper_qa_v1_2026-10-12_standard/reviews.json \
  --output evals/runs/paper_qa_v1_2026-10-12_standard/scoring
```

`PAPER_ANALYSIS_DISABLE_PROXY=1` 适用于本机代理未运行的环境；代理正常时按实际网络配置执行。额度按单次、单篇论文计算：该论文的 4 题共享一次 standard 额度（累计 300,000 tokens、16 次调用）；下一篇使用独立账本，不承接上一篇用量。每次输出上限 65,536、每题时限 420 秒沿用 standard 默认；light 和 deep 分别保持 100,000／16,384 与 600,000／98,304。额度上限不是实际用量。`--max-followups 0` 有意测量首轮能力，不能据此推断默认补取后的效果。不同论文的运行记录和总体 `baseline_manifest.json` 分开保存；输出目录禁止覆盖历史基线。

## 评价规则

先冻结参考，再运行系统；被测清单只有问题、图号和 PDF 指纹，不包含参考答案、gold claims 或 gold evidence。评价者逐条检查最终交付主张，包括金标准外的额外主张；正确的额外主张可计入主张正确率，不增加必需主张召回。等价表述可匹配；同一参考要求跨多条输出时须在判定理由写明共同支撑的主张 ID，全部内容满足才标记覆盖。

评价工作表绑定参考 SHA-256、run_id、answer_id 与回答文件 SHA-256；回答改变后旧评价失效。每条输出主张必须判定 `correct / incorrect / unverifiable`、引文正确性；视觉主张还须判定图号/子图对齐。必须评价不确定性和禁止推断，模板空值不能作为通过。

评分分别报告主张正确率、必需主张召回、引文正确率、子图对齐、状态匹配、30 道可回答题的完整通过率，以及 10 道不存在图号题的正确拒答率。每项都有分子/分母；没有输出主张的拒答，其主张正确率是 N/A，不是 100%。没有独立评价时仅计算确定性证据覆盖，语义指标保持未评价。配置/进程失败仍留在完整回答的分母中。

文本证据召回检查审计中同页片段是否包含定位锚点，可能漏掉等价的另一处证据，不等于语义检索召回。视觉输入覆盖只检查是否取得目标页面/子图的视觉证据记录，不表示模型读对。最终答案的正确性来自独立逐条评价，不能用服务内 fact checker 的 `supported` 或 QC `passed` 代替。

## 错误归因

每道失败题选一个有审计证据的主错误，其他问题记为次要错误。错误占比分母是失败题数，避免对同一失败多次计数。没有足够审计证据时使用 `unknown`。

| 分类 | 归因条件 |
|---|---|
| execution | 配置、HTTP、预算、超时或进程失败使必要阶段未执行 |
| parser | 原始 PDF 有证据，解析产物已缺失/错误或图定位错页 |
| retrieval | 解析产物有证据，但送入回答模型的片段没有必要内容 |
| vision | 页面可用，但直接视觉观察误读、漏读或无法形成可用观察 |
| answer | 必要证据已输入，草稿/最终主张仍错误、漏答或越界推断 |
| verification | 草稿正确且有原文支持，核验或确定性闸门错误剔除 |
| citation | 正确主张绑定错误引文、页码、图号或子图 |
| status | 核心内容正确，但 answered/partial/refused 或限制表达错误 |
| unknown | 现有产物不足以区分原因 |

检索/读图/回答三者按主错误数排序；执行、解析、核验问题另列为前置修复项。当前是调试校准集，同一样本反复优化后的成绩不能作为独立验收成绩；上线前应增加未参与调试的新论文留出集。

已知参考差异：DS-03 的图标签为 `cor=0.922`，旁边正文为 `0.923`；问题明确要求图标签。APN-03 的图标签为归一化 `Kd*=53.8 nM`，图注的 `Kd=323 nM` 是未归一化值。两处差异必须保留。
