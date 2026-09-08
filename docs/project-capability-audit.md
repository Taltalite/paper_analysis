# 项目能力与简历表述核对（2026-09-07—09-08）

本次依据实际源码、离线测试及当前 Kimi API 的真实调用核对，不把功能接口或 mock 测试等同于真实模型质量验证。

## 原状态的差距

| 简历描述 | 实际发现 | 本次处理 |
| --- | --- | --- |
| 多模态模型读取论文图片 | 有适配代码，但本地未配置视觉模型；真实基线 4 张图均为 `noop` | 用当前 `kimi-for-coding` 真实验证并在本地 `.env` 启用视觉模型 |
| OCR、图例及子图参与图文分析 | 视觉返回字段在证据合并和后续清洗时丢失，报告未展示 | 补齐 schema、证据合并、分析提示词、核验输入与报告传递 |
| 完整论文图表理解 | 原逻辑优先同页前四个嵌入位图，会丢失矢量图与部分子图 | 优先 2 倍分辨率的页面渲染，保留矢量线条、坐标轴及图中文字 |
| 跨页图表关联 | Figure 4 的图形位于第 7 页，图注在第 8 页，原输入只有图注页 | 增加保守的相邻页关联，真实复验识别 a–g 七个子图 |
| 结构修复后继续读图 | 结构化模型可能遗漏原图片路径或生成不存在的路径 | 以 parser 资产为准恢复关联，并保留被结构修复遗漏的原图 |
| 视觉失败时保守回退 | 异常被静默吞掉；未读图时将图注填入 OCR 字段，并可能给中置信度 | 日志及报告显示失败类型；noop 的 OCR 为空、置信度为低 |
| 图表语义缓存 | 缓存键遗漏正文引用；无效结构可能写入缓存；同路径 PDF 复用旧截图 | 缓存包含实际提示词，结构校验通过后才写入，重解析刷新截图 |
| 本地完整运行 | CrewAI 默认 memory 目录落在工作区外，在当前沙箱不可写 | 统一运行入口将 XDG_DATA_HOME 默认设置为工作区内缓存目录 |

## 已完成的真实验证

- **未启用视觉模型的完整论文基线**：`output/audit-baseline-pdf.md`、`output/audit-baseline-pdf.json`。4 张图均为 `noop`；报告虽能生成，但不代表进行了视觉识别。
- **合成图片验证**：`output/vision-verification/semantic.json`。图注和提示词不含柱子标签及数值，模型从图片正确提取 Alpha、Beta、37、83，来源为 `multimodal_llm`。
- **跨页图表复验**：`output/figure4-verification/semantic.json`。实际输入包含 `page_7.png` 与 `page_8.png`；返回 a–g 七个子图，保留缩略文档中文字不可可靠识别等不确定性。
- **复杂图表超时检查及复验**：Figure 2 首次请求触发 `ReadTimeout`，链路保留明确失败状态；新增 `VISION_REQUEST_TIMEOUT`，将本地等待时间设为 240 秒后单图复验成功，返回 5 个子图及 63 条可见文字，结果位于 `output/figure2-verification/semantic.json`。这说明接口可工作，不证明其中每条识别均准确。
- **离线契约测试**：真实生成和解析矢量 PDF，mock HTTP 响应，核对传输的 base64 确为渲染图片，并确认 OCR、图例、子图字段进入图表分析提示词和 Markdown。这类测试不调用真实模型。
- **API 测试**：健康检查及 PDF 任务创建、状态查询、报告和产物下载使用 fake 分析服务验证。当前沙箱内 TestClient 线程通信挂起，放开沙箱后 2 项测试通过；不将此描述为真实模型的 API 并发压测。

**完整多模态运行已完成**：最终产物为 `output/audit-complete.md`、`output/audit-complete.json` 和 `output/audit-complete.parsed.md`。四张图均为 `multimodal_llm`，Figure 1–4 分别返回 6、5、7、7 个子图，以及 42、63、49、26 条可见文字；共生成 4 项图表分析、16 项事实核验。图表分析没有自动回退。最终运行复用了前面真实视觉调用生成的缓存，正文理解、图表分析和事实核验仍走真实 CrewAI / Kimi 流程。

最终检查还发现视觉证据展示函数未被 Markdown 主模板调用；已接入 `6.4 视觉证据与解析状态`，将关键契约测试改为检查公开的 `render()` 入口。随后直接复用本次真实模型输出重新渲染 Markdown / JSON，没有再次调用模型。已核对最终报告包含四处真实视觉来源标记及 OCR、图例、子图证据。

离线验证：67 项单元测试、2 项 API 集成测试通过。这里的 16 项核验是流程输出数量，不是准确率指标。核验报告确实指出了若干证据不足或表述过强的主张；目前这些判定尚未全面约束报告其他章节，不能据此声称报告中所有结论均已被证实。

## 仍不应写入简历的能力

- **精确逐图裁剪 / 子图切割算法**：当前用整页及相邻页图像，子图划分来自视觉模型语义输出，没有完成通用区域定位或像素级裁剪。
- **医疗 RAG、临床指南检索、外部事实验证**：外部 RetrievalAdapter 仍只有契约，当前核验限于论文内部证据。
- **已完成医学质量基准或量化降幻觉效果**：校准集清单与标注模板不是已完成评测；本次功能 smoke 也不能用于声称医学准确率、临床效果或收益百分比。
- **稳定无误的证据闭环**：证据 ID 在结构修复后的重建、未获支持主张对正文报告的约束仍有待完善；数值规则为启发式，不具备通用数值语义核验能力。
- **严格 Token 总预算或已量化节省比例**：有重点章节选择、条件式结构修复和视觉缓存，但尚无统一调用账单评估，工具仍可访问较长章节。
- **任意扫描版 PDF 解析**：当前章节和图注发现依赖可提取文本，未实现通用扫描版全文 OCR；相邻页关联也只覆盖一类常见排版。

## 推荐简历措辞

> 基于 CrewAI 构建研究文献正文理解、图表分析与论文内部证据核验流程；通过多模态模型读取 PDF 页面图像，提取可见文字、坐标轴、图例及子图信息，并关联图注和正文生成结构化报告。实现视觉语义缓存、跨页图表关联及失败回退，完成合成图像与公开论文的真实接口验证。

这里的“证据核验”描述已实现的处理流程，不代表已证明生成结论全部正确。

## 复现入口

```bash
# 全部离线单元测试
bash scripts/run.sh python -m unittest discover -s tests/unit -p 'test_*.py'

# API 集成测试，无真实 LLM 调用
bash scripts/run.sh python -m unittest discover -s tests/integration -p 'test_*.py'

# 合成图真实视觉自检
bash scripts/run.sh python scripts/verify_vision.py

# 指定图表真实复验
VISION_REQUEST_TIMEOUT=240 bash scripts/run.sh python scripts/verify_vision.py \
  --pdf ref_baseline/s41467-025-64293-2.pdf --figure-id 'Figure 2' \
  --output output/figure2-verification

# 完整论文分析
INPUT_PATH=ref_baseline/s41467-025-64293-2.pdf \
OUTPUT_MARKDOWN_PATH=output/audit-complete.md \
OUTPUT_JSON_PATH=output/audit-complete.json bash scripts/run.sh
```

真实运行使用现有 Kimi 账号，原始输入为 Nature 已公开的开放获取论文：
[公开论文页面](https://www.nature.com/articles/s41467-025-64293-2)。本地 PDF 无批注、无嵌入附件；本次未发送简历或其他私有资料。原 README 对 Kimi Code 视觉能力的判断已依据真实调用更正，参见[官方图像输入配置说明](https://www.kimi.com/code/docs/en/third-party-tools/hermes.html)。
