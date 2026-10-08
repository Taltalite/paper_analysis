# Kimi + Qwen 真实冒烟（2026-10-03）

## 配置与范围

文本使用 `api.kimi.com / kimi-for-coding`；视觉使用 `token-plan.maas.qianwenaiapi.com/compatible-mode/v1 / qwen3.8-flash`。论文为 `ref_baseline/gkaf795.pdf`，SHA-256 为 `b8b9addf31732c1f3fd3f56b3009b9cbc9d22b0f5c03afecfe48355376cd5dee`，实际视觉输入为 PDF 第 9 页。

最初配置的 `qwen3-vl-flash` 在 Token Plan 端点返回 HTTP 404 `model_not_found`；同端点临时改用官方套餐支持的 `qwen3.8-flash` 后，合成图预检通过，读出仅在图像中的 Alpha、Beta、37、83。随后完成五场景真实论文测试。复核完成后本地 `.env` 仅将 `VISION_MODEL` 更新为 `qwen3.8-flash`，密钥与其余配置未改。

官方资料：[Token Plan 模型列表](https://platform.qianwenai.com/docs/token-plan/overview)、[套餐接入示例](https://platform.qianwenai.com/docs/developer-guides/clients-and-developer-tools/chatbox)。这属于接口兼容性验证，不证明该模型比其他视觉模型更准确。

## 结果

| 场景 | 最终状态 | 生成轮数 | 耗时（秒） | 交付 |
| --- | --- | --- | --- | --- |
| 正文 KL divergence | answered | 1 | 62.051 | 5 条正文主张 |
| Figure 4a 实线与阴影 | partial | 2 | 183.808 | 2 条图注主张、1 条视觉主张 |
| Figure 4a 位置 34/37 标签及颜色 | refused | 3 | 406.619 | 0 条主张 |
| 不存在的 Figure 99a | refused | 0 | 0.046 | 生成前拒答 |
| 关闭视觉后的曲线比较 | refused | 1 | 27.312 | 视觉不可用停止 |

五场景均已结束，原进程退出码 0。没有因聊天中断而重跑。八项现有工程检查均为 true，但这些检查不等于完整视觉调用成功或答案正确：其中 `no_model_error` 检查轮次 error/停止原因，并不覆盖 `visual_review.status=failed`；拒答没有视觉主张时，逐条复核检查会自然通过。

## 发现的问题

1. 原图复核发生误判：实线/阴影场景首轮，Qwen 将 A 子图的 U29–C39 范围误读为含 40+ 位置的标签，否决了相符的范围描述。第二轮删除该细节后，正式答案保留图注定义与稳妥视觉观察，复核通过。
2. 细小标签提取错误：OCR 出现 `nom⁵U34` 和 `m⁵C37`；页面复查可见红色 `ncm⁵U34` 与黑色 `m¹G37`。此处是本次页面复查观察，不替代专家金标准。
3. 标签题首轮直接复核 `failed`，现有审计未细分 HTTP、响应解析或逐条匹配错误，无法确认根因。第二轮复核继续混淆位置/颜色；累计两次复核调用，最终三轮后拒答。`budget_exhausted` 是问题轮次预算，不是账户余额或配额错误的证据。
4. 正式 `claims` 未放行上述错误标签，但最终 `uncertainties` 中仍含“上标字符按当前视觉证据可辨为‘⁵’”等判断。主张闸门没有覆盖全部自由文本，不能宣称用户可见输出已完全阻止错误信息。
5. 尚未记录真实 token 用量与计费，不能据耗时计算成本；没有专家准确率评分、浏览器交互测试或完整报告重跑。

## 产物与后续

运行目录 `evals/runs/qwen-smoke-2026-10-03/`（按仓库规则忽略）：`preflight.json` 保存当时临时覆盖的预检记录；`input.jsonl` 为五题；`manifest.json` 为运行清单；`review-summary.json` 为结果摘要；`questions/{id}/` 保存请求、答案与逐轮审计。run_id 为 `2f40eaeb-adbd-46d8-8e24-1b51473c7efa`。

后续优先：约束拒答/不确定性说明中的未核验断言；细分复核失败审计；验证目标子图裁剪或更高分辨率输入，再用人工冻结标注对比模型。不要仅因同一模型两次判断一致就视为可靠。人工材料见 [标注指南](../evals/annotation/README.md)。
