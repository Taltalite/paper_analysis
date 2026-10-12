# 固定样本评分：paper-qa-10-v1.1

参考状态：`ai_provisional`；评价类型：`ai_assisted`。

| 指标 | 分子/分母 | 比率 |
|---|---:|---:|
| 独立评价覆盖 | 40/40 | 100.0% |
| 输出主张正确率 | 65/69 | 94.2% |
| 必需主张召回 | 36/67 | 53.7% |
| 引文正确率 | 65/69 | 94.2% |
| 子图对齐 | 8/8 | 100.0% |
| 回答状态匹配 | 20/40 | 50.0% |
| 可回答题完整通过 | 0/30 | 0.0% |
| 不存在图号的正确拒答 | 10/10 | 100.0% |
| 文本证据定位召回 | 30/44 | 68.2% |
| 视觉证据输入覆盖 | 12/12 | 100.0% |

## 主错误分类

每道失败题只计一个主错误；次要错误保留在 JSON，比例分母为失败题数。

| 分类 | 题数 | 失败题占比 |
|---|---:|---:|
| status | 9 | 30.0% |
| vision | 5 | 16.7% |
| execution | 4 | 13.3% |
| retrieval | 4 | 13.3% |
| verification | 4 | 13.3% |
| parser | 2 | 6.7% |
| answer | 1 | 3.3% |
| citation | 1 | 3.3% |

检索/读图/回答优化顺序：vision → retrieval → answer。

## 逐题结果

| 问题 | 完整通过 | 主错误 | 漏掉的必需主张 | 判定理由 |
|---|---|---|---|---|
| DS-01 | 否 | verification | G2 | 最终漏掉 BRNN 必需主张。草稿 c2 的 BRNN 与四个 17 长度输入向量均有当前输入支持，核验为 supported；确定性闸门因草稿引文写成 nucleo- tides、摘录为 nucleotides 而剔除整条。是断词差异触发的核验误杀，不是必要证据未检索到。仅使用 9,491 tokens、2 次调用，却返回 budget_exhausted，停止原因也需修正。 |
| DS-02 | 否 | answer | — | 两条必需摘要指标回答正确，但增加了错误的 read-level 限定；内部 checker 仍判 supported、QC passed，不能替代独立正确性评价。输入已含正确摘要，问题要求未要求推断评价粒度，主因是回答扩展越界。 |
| DS-03 | 否 | execution | G1, G2 | 目标 PDF 第 7 页实际输入 Qwen 成功；其输出投影只保留 general direct_evidence，没有把 cor 标签送入回答证据。之后 Kimi HTTP 成功但草稿未形成，audit.draft=null、model_error；无完整类型诊断，不能断言具体 JSON 错因。主要失败为生成/结构化阶段，视觉证据投影遗漏记次要问题。 |
| DS-04 | 是 | — | — | 独立检查本 PDF 全文没有 Figure 99a，系统明确拒答、无其他图替代、无虚构主张，说明解析范围限制。 |
| APN-01 | 否 | execution | G1, G2 | 所选第 2 页 Figure 1 图注及第 5 页正文已包含 TdT/FdUTP 聚合与 3′端 Atto 疏水嵌段自组装的完整机制。Kimi HTTP 成功（6,126 tokens）后未形成可用草稿，audit.draft=null、model_error；现有脱敏审计未保存具体结构化异常类型。主因是生成/输出契约阶段失败，不能因参考第 1 页锚点未命中就归为检索缺失。 |
| APN-02 | 否 | status | — | 三条实验结果及条件有原文支持、必需内容已覆盖，无患者疗效外推；但最终在 answered、QC passed 时仍声称“相关草稿尚未核实”，draft.sufficient=true、evidence_gaps=[]，该限制表达与实际交付矛盾。主错误记为状态/不确定性表达，不记为科学数值错误。 |
| APN-03 | 否 | verification | G1 | 原图、Qwen 的子图 b OCR/summary、回答草稿都正确给出 Kd*:53.8 nM，并区分未归一化 323 nM。由于规范化后标签仅 10 字符，quality_control 和 qa_quality 的 ≥12 字符定位阈值丢弃唯一引文，整条视觉主张被剔除；直接看图复核甚至没有启动。低用量返回 budget_exhausted 是附带停止原因错误，主因核验误杀。 |
| APN-04 | 是 | — | — | 完整检查该 PDF 不存在 Figure 99a；最终明确拒答，没有其他图替代或虚构主张，并声明解析范围限制。 |
| ENDO-01 | 否 | status | — | 最终已正确覆盖 end repair 与重复/末端加工定位限制，额外 CSI 主张也正确。未发布的可选 claim_4 被部分支持判定剔除后，系统仍把已满足核心问题的交付标为 partial，并笼统声称不足以完整回答；主因状态/限制与问题需求不对齐。 |
| ENDO-02 | 否 | verification | G2 | 提高 cut-off 导致数据减少的草稿 c2 原文机制/图注可支持，checker 判 supported，仅将中文内引号“it also”改成 ASCII 双引号；确定性 claim_mismatch 因这种文字差异剔除整条。主因核验误杀。输入对跨页句子截断、正文误归图注是次要 parser/retrieval 问题。 |
| ENDO-03 | 否 | execution | G1, G2 | PDF 第 6 页目标子图进入 Qwen，视觉观察有单调下降趋势，但送入回答模型的 summary/OCR 未保留端点近似值，不能独立确认最高 cut-off 的比例。随后生成阶段 HTTP 已结算却无可用 draft，model_error；主因执行/输出契约失败，视觉证据投影的缺失另记。 |
| ENDO-04 | 是 | — | — | 独立全文检查没有 Figure 99a；最终明确拒答、无虚构或其他图替代，说明解析范围限制。 |
| MOD-01 | 否 | citation | G3 | 最终未明确 prediction score 是 Dorado 的修饰概率。正确草稿 c3 的两条引文都位于 p3_b54，却同时引用 p7_b3，后者没有对应引文，确定性闸门因此正确拒绝这组引文绑定。主因草稿过度引用导致必需定义被撤回，记 citation；不把每一次剔除都算作核验误杀。 |
| MOD-02 | 否 | retrieval | G1 | 位置、对照和邻位效应基本正确，但未明确 U47 的 Ψ 概率分布/KL divergence 比较这一必需参考要求。PDF 第 10 页独立段落完整说明该机制和 elevated KL at U47，parsed 有该段，当前选取只到 p10_b1 的其他修饰邻位效应，未取到目标段落；主因检索漏段。仍标 answered 且通用未核实提示是附带状态问题。 |
| MOD-03 | 否 | vision | G1, G2, G3, G4 | Qwen 初次观察识别 ncm5U34/m1G37，但送入 Kimi 的目标 panel summary/OCR 未表达标签颜色及上标排版，无法覆盖 4 条视觉要求。Kimi 对摘录的上标缺失作出保守限定；直接图像复核却把“摘录无法确认”当作“原图无法辨认”判冲突，进一步撤回已知标签。主因视觉属性提取/投影不完整；核验对证据层级的混淆是次要问题。 |
| MOD-04 | 是 | — | — | 本 PDF 全文没有 Figure 99a；最终明确拒答、无替代图或虚构主张，声明解析范围限制。 |
| HIST-01 | 否 | retrieval | G1, G2 | Box 1 的第 2 页正文 p2_b6 在 parsed.json 完整存在，明确 constant voltage、enzyme ratchet 和 ionic current；当前只检索到 Box 1 标题、文章标题和引言背景，未把框内正文送入回答模型。模型因此合理拒答；主因检索漏掉标题邻接正文，非 parser 无法提取。 |
| HIST-02 | 否 | parser | — | 机制与不能证明单碱基分辨率的两条核心要求正确，额外实验细节也正确；但把时间线框内文字当作正式图注，源自 parser 的 caption 边界过度吸纳。主错误为 parser 导致的来源误标；另有核心已覆盖却 partial 的状态问题。 |
| HIST-03 | 否 | vision | G1, G2 | 实际原图中 2014 MAP、2015 E.coli 组装 99.4% 清晰；初次 Qwen 的全图 evidence 投影仅保留时间轴总体结构和 2012 连接数，丢掉所问事件/年份。Kimi 正确承认当前摘录缺信息，复核却将“摘录缺失”当成“原图没有”而判冲突，无法补回事实。主因视觉信息投影，次要核验作用域错误。 |
| HIST-04 | 是 | — | — | 本 PDF 全文没有 Figure 99a；最终明确拒答、没有其他图替代或虚构主张，说明解析范围限制。 |
| HMM-01 | 否 | execution | G1, G2, G3 | 所选第 1 页 p1_b3/p1_b5/p1_b6 已有不需 chemical treatment、Gaussian 6-mer emission 与 HMM 模型，必要答案可获得；Kimi HTTP 成功结算 4,772 tokens 后 draft=null、model_error。主因生成/输出契约执行阶段，现有日志不足以定位更细的结构异常。 |
| HMM-02 | 否 | status | — | 三条必需结果全部正确且引文定位正确，无 accuracy/覆盖率混淆；最终 answered/QC passed 仍附“相关草稿尚未核实”，与 draft.sufficient=true、无证据缺口的审计不一致，主因通用不确定性表达。 |
| HMM-03 | 否 | status | — | 原图、最终两条视觉主张、引文及子图对齐均正确，所有必需内容已覆盖，直接看图复核也支持。却因观察存在非关键近似不确定性降为 partial，stop_reason 同时 completed，并提示未核实/不足以完整回答；主因状态与限制表达不一致。 |
| HMM-04 | 是 | — | — | 本 PDF 全文无 Figure 99a；最终明确拒答，无替代图或虚构主张，并说明解析范围限制。 |
| CHN-01 | 否 | status | — | 两条必需摘要结果正确、引文正确且未混用模拟中的其他数字；最终 answered/QC passed 仍附“相关草稿尚未核实”，draft.sufficient=true、evidence_gaps=[]。主错误是通用不确定性表达，不是数字读取。 |
| CHN-02 | 否 | status | — | 所有必需内容、引文和范围均正确，核验为 supported、QC passed、草稿 sufficient=true/evidence_gaps=[]，最终仍声称“相关草稿尚未核实”。通用不确定性与已完成核验不一致，严格交付失败归状态。 |
| CHN-03 | 否 | vision | G1, G2 | 最终因核验/闸门拒答，没有发布主张。原始 Qwen 缓存 direct_evidence 已正确绑定 sub 的 raw/filtered=4.91±0.47%/4.73±0.46%，indel=16.67±0.47%/2.66±0.19%，并解释浅色/深色类别；向问答投影时只保留 panel summary 和 visible_text 列表，丢失正确关系。Kimi 草稿随后误将 filtered indel=4.73%、filtered sub=2.66%。加和不能消除这两个值互换的歧义。checker 又放行错误配对的算术比较，确定性主张文本差异挡住该条；主因是视觉证据投影，回答和核验为次因。账本 33,012 tokens/7 次调用，budget_exhausted 也不是真实额度耗尽。 |
| CHN-04 | 是 | — | — | 原 PDF 未含 Figure 99a；目标图不存在时在 LLM 生成之前明确拒答，没有引用其他图替代。 |
| SUS-01 | 否 | verification | G1 | 最终漏掉 G1 的 Bhattacharyya distance，草稿 c1 正确且 checker supported，实际摘要 min- imize 等断词导致引文闸门剔除该关键主张。已检索到摘要的必需信息，主因是核验定位误杀。额外 c2 将输入片段未解释的 BD-DTW 推成论文内部可能未解释，原文第 2 页明确已定义，属于回答/引用错误；不确定性又把局部摘录限制扩大为论文术语问题。 |
| SUS-02 | 否 | status | — | 必需主张和引文全部正确，核验/QC 均通过、草稿无必要证据缺口，但最终使用“草稿尚未核实”的通用不确定性，严格交付失败归状态。 |
| SUS-03 | 否 | status | — | 目标子图与所有必需科学内容、引文、直接复核均正确，草稿 sufficient=true/无必要缺口、QC passed、stop_reason completed；最终仍 status=partial，声称当前证据不足以完整回答以及草稿尚未核实。无关图像不确定性与已通过逐条复核不应自动否定完整回答，主错误归状态。 |
| SUS-04 | 是 | — | — | 完整 PDF 无 Figure 99a；生产解析未定位该图并在生成前明确拒答，未替用其他图。 |
| RARE-01 | 否 | parser | — | 两个 Recall 数值与百分点解释正确；额外自述“Figure 1c 图注”实际引用了第 4 页分析正文。parsed ordered_blocks 为 text，但 figures 又将该块定义为 Figure 1C，运行证据把它标作 caption，引发错误出处自述。主因 parser 图注识别，引用与通用未核实提示为次因。 |
| RARE-02 | 否 | retrieval | G2 | 原 PDF 第 7 页 Traceable reasoning chain validation 明确包含 180 病例、八个数据集、总专家池 10 位、每例 3 位独立评审并取平均。生产 parsed p7_b3 保留这些文字，但送入本题的 4 个片段只含截断图注/摘要等，没有这段关键正文，漏掉 G2。当前输出对摘要与有限图注的范围限定基本恰当，主因检索漏取完整验证段落；停止原因 budget_exhausted 仍与仅 19,509 tokens/4 次调用不符。 |
| RARE-03 | 否 | vision | G1, G2 | 最终数值/名称正确，但最大类名称和 n=82 来源标为正文，未完成两条 gold 的直接视觉要求。Qwen 原始缓存的 panel.legend_items 和顶层 visible_text 已包含 Reasoning weighing error (n=82)，投影成问答证据时只保留 panel summary+visible_text，丢掉 legend_items；Kimi 因此正确说明名称/计数依赖正文。独立看图复核事实上读到了所有图例，但结果未补回回答证据，主因视觉证据投影。最终还使用尚未核实的通用提示。 |
| RARE-04 | 是 | — | — | 原 PDF 全文与图号清单均无 Figure 99a；生成前拒答且没有采用其他图替代。 |
| ADDUCT-01 | 否 | retrieval | G1 | 漏掉 G1 的 DNA 分离→化学/酶水解释放→LC-MS 定量流程。原 PDF 第 2 页及 parsed p2_b4 都清楚保留该流程，但本题只选入 p1_b30/p1_b33/p3_b3/p7_b4，未取到 LC-MS 段。科学内容和有限证据范围限定基本正确，主要为检索漏取必需方法。仅 12,282 tokens/2 次调用，budget_exhausted 为次要状态错误。 |
| ADDUCT-02 | 否 | status | — | 两条必需主张和全部补充/引文正确，核验/QC 均通过、草稿无必需证据缺口，但最终仍声称“相关草稿尚未核实”。严格交付失败归状态，不能据此认定化学解释错误。 |
| ADDUCT-03 | 否 | vision | G1, G2 | 原始 Qwen visible_text 保留横轴有序刻度 4000/3000/2000/1000/0，但整图投影只使用 direct_evidence，不包含这些刻度和 axes；Kimi 因此正确指出当前摘录无法判断左右/方向，没有完成 G1/G2。直接看图复核又明确观察到横轴递减、最高点在 1000 右侧，但这些附带观察未反馈到回答证据。主因视觉证据转换。账本 39,503 tokens/8 次调用，budget_exhausted 也不是真实预算耗尽。 |
| ADDUCT-04 | 是 | — | — | 该 PDF 无 Figure 99a；运行在目标图不存在时明确拒答且没有其他图替代。 |

文本召回按同页原文定位片段匹配；视觉输入覆盖只说明目标页面证据可用。两者均不替代主张语义正确性。10 道不存在图号题单列，不能抬高 30 道可回答题的通过率。
