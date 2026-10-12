# 问答运行与评价边界

当前准确率评价使用 [10 篇论文 / 40 题参考集](datasets/paper_qa_v1/README.md)，完整基线见 [评分与错误分类](baselines/paper_qa_v1_2026-10-12/README.md)。参考由本会话助手独立标注，状态为用户授权的 `ai_provisional`，Kimi/Qwen 仅接受固定问题并作为被测模型；参考答案不会输入被测模型。评分协议、正式运行命令与独立评价工作表以参考集说明为准。

## 保留的工程候选与 smoke

`qa_candidates.jsonl` 保留 16 条工程候选：QA-01–12 是待绑定论文的表观遗传学问题类型，QA-13–16 绑定本地 MoDorado PDF、图号和子图。后四条属于生物信息/RNA 修饰。`qa_smoke.jsonl` 保留正文、子图、缺图、无视觉降级四个场景。这两份清单继续兼容 `run_qa_batch.py`，不是参考答案或专家样本。

```bash
# 默认只检查输入绑定，不调用模型
bash scripts/run.sh python scripts/run_qa_batch.py --output evals/runs/qa-preflight
bash scripts/run.sh python scripts/run_qa_batch.py \
  --manifest evals/qa_smoke.jsonl --output evals/runs/qa-engineering-preflight
# 真实执行添加 --real，且使用新的输出目录；--ids QA-13,QA-14 可缩小范围
```

真实执行会把所选论文内容发送至配置的模型端点，需确认源数据和服务配置可用于该运行方式。准备检查无需外部请求。未绑定或指纹不符不调用，配置错误与执行错误分别记录；结果保留 run_id、任务/答案 ID、审计路径、用量及确定性工程检查。

## 评价契约

- **实现验证**：mock/fake 模型、合成 PDF 和 API 回归检查接口、预算、定位、拒答与失败处理。
- **真实调用**：记录日期、请求参数、响应型号、后端答案 ID 和供应商用量；接口成功不能替代正确性评价。
- **独立评分**：绑定冻结参考与模型输出，由独立阅读评价逐主张、证据、子图对齐和拒答，报告样本数与每项分母。AI 暂定参考与专家仲裁分别标识，内部 checker 不作最终裁决。

页码采用 PDF 的 1-based 物理页码。视觉证据记录实际图形观察与子图标签，图注复述不能充当直接读图证据。兼容候选流程的 `expert_evaluation` 仍为 `not_evaluated`；当前 40 题 AI 辅助校准评分另存于正式基线。

## 已退役材料与历史记录

旧 `annotation/`、`qa_annotation_template.json`、`datasets/paper_v1/` 和人工指南已归档；五份已填写初标保持单人待复核身份。原文件与恢复说明在本地 `evals/archive/` 保留，不随仓库同步。

任务、发布行为与验收边界见 [README](../README.md)。历史验收、说明文档与本机 smoke 日志仅在开发工作区保留。
