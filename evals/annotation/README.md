# 人工标注操作说明

本目录的文件是供人工填写的材料，不是已经完成的金标准，也不表示模型答对了。原有 `evals/qa_annotation_template.json` 保留兼容；本目录 `manual-qa-v1` 是更详细的人工工作表，尚未接入自动评分器。

## 文件与起步方法

- `blank.json`：任意论文/问题的空白模板。
- `ANNOT-01.json` 至 `ANNOT-05.json`：已绑定 `ref_baseline/gkaf795.pdf` 的五个任务，覆盖正文、图注与图像区分、细小上标/颜色、曲线观察和不存在的图。答案全部留空。
- 复制每个任务为 `ANNOT-01.A.json`、`ANNOT-01.B.json`，分别给两位标注人员。先不要阅读模型答案、历史冒烟结论或另一人的标注。

这五题只适合启动校准，不足以代表全领域效果。后续扩展到多篇论文、不同版式与困难图表；调试集和最终验收集分开，避免反复针对同一论文改提示词后把结果当作独立验证。

## 第一步：确认输入

确认打开的 PDF 与 `paper.sha256` 一致；论文重新下载或文件改变后应重新绑定。填写题名和自己的匿名 `annotator_id`。页码一律使用从 1 开始的 PDF 物理页码，不使用论文印刷页码。填写日期可记录在仲裁备注中。

## 第二步：先找证据，再写答案

1. 阅读问题涉及的正文、方法、图注和实际子图，必要时放大原图。
2. 为每段证据新增 `E1`、`E2` 等编号。`source_kind` 使用 `text`、`caption` 或 `vision`。
3. 正文/图注填写 `verbatim_quote`，保留原文；图像填写 `visual_observation`，用中文描述真正可见的坐标轴、标签、颜色、走势或数值。
4. 填写 `pdf_page_1_based`、图号/子图；`block_id` 和 `bbox` 不知道时保留 null，不编造。bbox 若填写，采用 PDF 点坐标 `[x0,y0,x1,y1]`、左上原点，并在同一页面验证。
5. `legibility` 使用 `clear`、`ambiguous`、`unreadable` 或 `not_applicable`。读不清的上标不可按领域常识补全，也不可根据先前模型答案补全。

图注明确“阴影是标准差”，属于 caption 证据；图像看见“曲线周围存在阴影”，才是 vision 观察。不要混为一种来源。保留源文中的修饰符、单位和条件；纠正排版断行不能改变内容。

## 第三步：形成参考主张

`gold_claims` 每项只写一条可独立判断的事实：`claim_id` 使用 G1、G2；`statement` 写中文参考陈述；`basis` 使用 text 或 visual；`evidence_ids` 引用本文件 E 编号。`required=true` 表示完整回答不可缺少，false 表示可选补充。图文混合结论尽量拆开并分别绑定证据。

`expected_status` 使用：

- `answered`：证据支持问题要求的完整回答。
- `partial`：仅部分问题可回答，必须说明剩余不确定性。
- `refused`：没有足够证据回答核心问题，包括目标图不存在。

填写 `required_uncertainties`（必须说明的限制）和 `forbidden_inferences`（不允许推断的结论）。例如可禁止从相关性推断因果；这里是方法示例，不是任何实际任务的参考答案。

拒答题可将 `gold_claims` 设为 []，但仍须记录拒答理由及查找范围。不存在的图不能编造页码或图像证据，可在 `adjudication.resolution` 记录核查范围。删除不用的空白占位项，未完成字段保持 null，不能用 0 冒充未知。独立填写完毕后将状态改为 `已独立标注`。

## 第四步：双人复核与冻结

两人分别完成后，比较主张、证据来源、可读性和回答状态。分歧在 `adjudication.disagreements` 中逐条记录，由第三人或讨论后仲裁；保留两份原始标注。合并文件记录 `reviewer_ids`、`resolution` 和 ISO 8601 格式 `frozen_at`，状态设为 `已仲裁冻结`。未解决的分歧不可进入正式计分集。

暂时只有一位标注人员时可以先推进，状态标为 `单人初标待复核`，不要声称双人金标准。冻结后修改必须另存版本并说明原因。

## 第五步：独立评价模型答案

金标准冻结后才打开模型结果，填写 `evaluation.answer_id`、`run_id`。逐条实际输出主张在 `claim_reviews` 中记录：

```json
{
  "answer_claim_id": "实际输出中的 ID",
  "matched_gold_claim_ids": ["G1"],
  "correctness": "correct / incorrect / unverifiable",
  "citation_correct": null,
  "panel_aligned": null,
  "reason": "人工判定理由与证据"
}
```

以上斜杠枚举说明填写时选择其中一个；布尔字段填写 true/false，不适用时 null。正确但未在金标准列出的额外主张需人工核查，不能直接判错或事后默默加入原金标准。将漏掉的必需主张写入 `missed_gold_claim_ids`，比较状态后填写 `expected_status_match`。

分别报告主张正确率、有效引文比例、目标子图对齐、必需主张召回和拒答判定；注明分子、分母、不适用项与样本数。拒答没有输出主张，不能把它的主张正确率算作 100%。模型自己复核通过、API 成功和工程检查通过都不属于人工正确性评分。

本目录不提供自动评分的假象；现在可人工填写与汇总，后续接入 schema 校验和可重复评分器。
