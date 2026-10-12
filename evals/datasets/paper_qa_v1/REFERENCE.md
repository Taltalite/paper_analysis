# 10 篇论文的暂定参考答案与证据

版本：`paper-qa-10-v1.1`；状态：AI 暂定参考（`ai_provisional`）。

本次 Codex 会话按用户明确授权独立阅读原文与实际 PDF 页面后形成。用户指定本会话答案为暂定 ground truth；模型身份以客户端选择为准，不从项目 API 配置推断。未经第二位独立专家复核，reference_status=ai_provisional。已有 MoDorado 单人初标仅作辅助，并重新核对原图；不计为专家仲裁。

参考文件 SHA-256：`39f4fc6e2466660d2e884781e551d46e11882613f8ec4419324badc2b31eafaa`。页码为从 1 开始的 PDF 物理页码；引文仅作定位，完整论断须阅读相应段落。直接视觉主张已检查实际页面，不能用图注代替。

修订记录见 [CHANGELOG.md](CHANGELOG.md)；运行前冻结的 v1.0 原样保留。v1.1 仅纠正 RARE-02 的原文范围与人数，不修改固定问题。

## DS — DeepSignal: detecting DNA methylation state from Nanopore sequencing reads using deep-learning

DOI：10.1093/bioinformatics/btz276；文件：`ref_baseline/bioinformatics_35_22_4586.pdf`；10 页；SHA-256：`61de64054fde8296a61eda15898ebcb422cd186cb5265dc9c51665008949bc5b`。

### DS-01 — DeepSignal 的 signal feature module 与 sequence feature module 分别使用什么网络，两类特征怎样用于最终预测？

参考状态：`answered`。

signal feature module 用 CNN 从原始电信号提取特征。；sequence feature module 用双向循环神经网络 BRNN 从信号信息序列提取特征。；两类特征拼接后送入全连接神经网络，预测甲基化状态。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | signal feature module 用 CNN 从原始电信号提取特征。 | text | E1 |
| G2 | sequence feature module 用双向循环神经网络 BRNN 从信号信息序列提取特征。 | text | E2 |
| G3 | 两类特征拼接后送入全连接神经网络，预测甲基化状态。 | text | E3 |

- E1：PDF 第 2 页，text。“uses convolutional neural network (CNN)”
- E2：PDF 第 2 页，text。“uses bidirectional recurrent neural network (BRNN)”
- E3：PDF 第 2 页，text。“features built from two modules are concatenated and fed into a fully connected neural network”

### DS-02 — DeepSignal 摘要报告的 2× 和 20× coverage 分别对应什么评价结果？请区分 accuracy 与 correlation。

参考状态：`answered`。

2× reads coverage 下，检测 5mC 和 6mA 的 accuracy 超过 90%。；20× reads coverage 下，DNA CpG 甲基化预测与 bisulfite sequencing 的相关性约为或超过 0.90。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 2× reads coverage 下，检测 5mC 和 6mA 的 accuracy 超过 90%。 | text | E1 |
| G2 | 20× reads coverage 下，DNA CpG 甲基化预测与 bisulfite sequencing 的相关性约为或超过 0.90。 | text | E2 |

- E1：PDF 第 1 页，text。“90% above accuracy for detecting”
- E2：PDF 第 1 页，text。“achieves 90% correlation with bisulfite sequencing”

证据边界：不得将 correlation 写成分类准确率；不得把 20× 的结果当作 2× 的结果。

### DS-03 — 只读 Figure 2 的图中标签：HX1 的 A、B 子图各标注什么 cor 值，哪个更高？

参考状态：`answered`。

A 子图标注 cor=0.922。；B 子图标注 cor=0.886，因此 A 的相关性更高。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | A 子图标注 cor=0.922。 | visual | E1 |
| G2 | B 子图标注 cor=0.886，因此 A 的相关性更高。 | visual | E2 |

- E1：PDF 第 7 页，vision，Figure 2a。A 图上方写着 HX1, cor=0.922；此处按照图标签读取，正文相邻段落写作 0.923，二者有末位差异。
- E2：PDF 第 7 页，vision，Figure 2b。B 图上方写着 HX1, cor=0.886。

证据边界：不得用正文 0.923 替代问题要求的图中标签 0.922。

### DS-04 — 请根据这份 PDF 的 Figure 99a 说明实验结果；如果不存在该图，请明确拒答，不要用其他图替代。

参考状态：`refused`。

这份 PDF 中不存在 Figure 99a，无法按该图说明实验结果。

已核查本 PDF 第 1–10 页的正文、主图、图注及附带页；没有 Figure 99 或 99a。范围只限这一份 PDF，不推断未提供的独立补充文件。

证据边界：不得编造 Figure 99a 的结果、页码或证据。

## APN — Enzymatic Synthesis of Aptamer-Polynucleotide Nanoparticles with High Anticancer Drug Loading for Targeted Delivery

DOI：10.1021/acs.biomac.3c00888；文件：`ref_baseline/deshpande-et-al-2023-enzymatic-synthesis-of-aptamer-polynucleotide-nanoparticles-with-high-anticancer-drug-loading-for.pdf`；10 页；SHA-256：`47e3155d8a5e6f4093a08a6d04be95f660f2b3ec8d3ad78c2b1c7c329280e977`。

### APN-01 — sgc8c-poly(FdU)-Atto 胶束如何用 TdT 构建？FdUTP 和 Atto-dUTP 分别起什么作用？

参考状态：`answered`。

TdT 把 5-FdUTP 聚合到适配体 3′ 端，形成承载核苷酸前药的 poly(FdU) 链。；随后在该链 3′ 端添加疏水的非天然 Atto-dUTP，形成两亲性聚合物并自组装为胶束。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | TdT 把 5-FdUTP 聚合到适配体 3′ 端，形成承载核苷酸前药的 poly(FdU) 链。 | text | E1 |
| G2 | 随后在该链 3′ 端添加疏水的非天然 Atto-dUTP，形成两亲性聚合物并自组装为胶束。 | text | E2 |

- E1：PDF 第 1 页，text。“polymerize 5-fluorodeoxyuridine triphosphate (5-FdUTP) onto the 3′-end of an aptamer”
- E2：PDF 第 5 页，text。“hydrophobic unnatural nucleotide”

### APN-02 — CCRF-CEM 细胞毒性实验中，floxuridine 与胶束的 cell viability 分别是多少？请报告误差、处理条件和统计检验。

参考状态：`answered`。

细胞先用高于 CMC 的制剂处理 4 h，洗去未结合多核苷酸，再在无药培养基继续培养。；floxuridine 对照的存活率为 89.9±1.7%，胶束为 60±8.6%。；胶束毒性更高；Tukey’s multiple comparison test，p<0.005。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 细胞先用高于 CMC 的制剂处理 4 h，洗去未结合多核苷酸，再在无药培养基继续培养。 | text | E1 |
| G2 | floxuridine 对照的存活率为 89.9±1.7%，胶束为 60±8.6%。 | text | E2 |
| G3 | 胶束毒性更高；Tukey’s multiple comparison test，p<0.005。 | text | E3 |

- E1：PDF 第 7 页，text。“micelles for 4 h at a concentration above their CMC”
- E2：PDF 第 7 页，text。“89.9 ± 1.7% and 60 ± 8.6%”
- E3：PDF 第 7 页，text。“p < 0.005, Tukey’s multiple comparison test”

证据边界：这是细胞实验，不得外推为患者疗效或体内安全性；不得把存活率当杀伤率。

### APN-03 — 只看 Figure 3B 曲线旁的文字：归一化解离常数 Kd* 的数值和单位是什么？

参考状态：`answered`。

图中曲线旁标注 Kd*=53.8 nM。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 图中曲线旁标注 Kd*=53.8 nM。 | visual | E1 |

- E1：PDF 第 4 页，vision，Figure 3b。橙色曲线旁的文字为 Kd*=53.8 nM；不是图注中的未归一化 Kd=323 nM。

证据边界：不得用未归一化的 323 nM 替代图中 Kd*=53.8 nM。

### APN-04 — 请根据这份 PDF 的 Figure 99a 说明实验结果；如果不存在该图，请明确拒答，不要用其他图替代。

参考状态：`refused`。

这份 PDF 中不存在 Figure 99a，无法按该图说明实验结果。

已核查本 PDF 第 1–10 页的正文、主图、图注及附带页；没有 Figure 99 或 99a。范围只限这一份 PDF，不推断未提供的独立补充文件。

证据边界：不得编造 Figure 99a 的结果、页码或证据。

## ENDO — ENDO-Pore: high-throughput linked-end mapping of single DNA cleavage events using nanopore sequencing

DOI：10.1093/nar/gkab727；文件：`ref_baseline/gkab727.pdf`；11 页；SHA-256：`32c61b16fced7edf35db6a5c278d70f1abf32b649b0c62385125a780046ea4ff`。

### ENDO-01 — ENDO-Pore 的 end repair 对 5′/3′ overhang 如何处理，这给重复切割事件的定位带来什么限制？

参考状态：`answered`。

end repair 填平 5′ overhang、去除 3′ overhang，平端保持不变。；经该处理后，报告的是各链最靠近 3′ 端的切割位置，不能保证重建更早的所有切割事件。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | end repair 填平 5′ overhang、去除 3′ overhang，平端保持不变。 | text | E1 |
| G2 | 经该处理后，报告的是各链最靠近 3′ 端的切割位置，不能保证重建更早的所有切割事件。 | text | E2 |

- E1：PDF 第 4 页，caption，Figure 1。“fill-in 5′ overhangs and remove 3′ overhangs, while blunt ends remain intact”
- E2：PDF 第 3 页，text。“CSI will only report the cleavage locus that is closest to the 3′ end of each strand”

证据边界：不得声称能保留所有原始断端或重建每次重切割的时间顺序。

### ENDO-02 — ENDO-Pore 的 pUC19 consensus benchmarking 使用 ≥5 repeats 时，median accuracy 和 first quartile 各约多少？提高 cut-off 有何代价？

参考状态：`answered`。

≥5 repeats 时，median accuracy 约 99.6%，first quartile 约 99.4%。；提高 repeat cut-off 会减少保留的数据量。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | ≥5 repeats 时，median accuracy 约 99.6%，first quartile 约 99.4%。 | text | E1 |
| G2 | 提高 repeat cut-off 会减少保留的数据量。 | text | E2 |

- E1：PDF 第 4 页，text。“A median accuracy of ∼99.6% with a first quartile of ∼99.4%”
- E2：PDF 第 5 页，text。“produced a reduction in the data output”

证据边界：这些是 consensus sequence accuracy，不得写成全体切割位点检测召回率。

### ENDO-03 — 只看 Figure 3B：repeat cut-off 从 1 提高到 7 时，proportion of data retained 如何变化？最高 cut-off 下是否仍保留一半以上？

参考状态：`answered`。

保留比例随 cut-off 增大单调下降，从约 1 降到低于 0.1。；cut-off=7 时远低于一半。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 保留比例随 cut-off 增大单调下降，从约 1 降到低于 0.1。 | visual | E1 |
| G2 | cut-off=7 时远低于一半。 | visual | E1 |

- E1：PDF 第 6 页，vision，Figure 3b。曲线在 cut-off=1 约为 1；随后逐点降低；cut-off=7 在 0 和 0.1 之间。

证据边界：只能给出图上可辨的近似范围，不编造未标注的精确原始值。

### ENDO-04 — 请根据这份 PDF 的 Figure 99a 说明实验结果；如果不存在该图，请明确拒答，不要用其他图替代。

参考状态：`refused`。

这份 PDF 中不存在 Figure 99a，无法按该图说明实验结果。

已核查本 PDF 第 1–11 页的正文、主图、图注及附带页；没有 Figure 99 或 99a。范围只限这一份 PDF，不推断未提供的独立补充文件。

证据边界：不得编造 Figure 99a 的结果、页码或证据。

## MOD — MoDorado: enhanced detection of tRNA modifications in nanopore sequencing by off-label use of modification callers

DOI：10.1093/nar/gkaf795；文件：`ref_baseline/gkaf795.pdf`；15 页；SHA-256：`f47a24c8b1717944ca1a7bef018778290c8a86851709e44a1ffa63db5df02e75`。

### MOD-01 — MoDorado 使用 KL divergence 比较哪些预测分布？请说明样本对照关系与 prediction score 的含义。

参考状态：`answered`。

比较同一核苷酸位置的修饰 RNA 样本与未修饰对照样本的 prediction score 分布。；修饰样本可以是 WT；未修饰对照可以是相应 gene deletion strain 或 IVT RNA。；prediction score 表示 Dorado 预测的修饰概率，而不是原始电流。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 比较同一核苷酸位置的修饰 RNA 样本与未修饰对照样本的 prediction score 分布。 | text | E1 |
| G2 | 修饰样本可以是 WT；未修饰对照可以是相应 gene deletion strain 或 IVT RNA。 | text | E2 |
| G3 | prediction score 表示 Dorado 预测的修饰概率，而不是原始电流。 | text | E3 |

- E1：PDF 第 7 页，text。“MoDorado compares the distribution of prediction scores at a particular position”
- E2：PDF 第 7 页，text。“between a modified RNA (i.e. wt) and an unmodified control”
- E3：PDF 第 4 页，text。“representing a predicted probability of modification from 0 to 1”

证据边界：不得将其说成模型与模型之间或原始电流分布的 KL 比较；高 KL 不等于确定某种化学修饰。

### MOD-02 — 论文中 Ψ caller 对 Trm8-dependent m⁷G46 的 off-label 检测，是直接在 G46 输出概率吗？实际比较哪个位置，为什么？

参考状态：`answered`。

通过比较 WT 与 trm8Δ 在相邻 U47 的 Ψ 概率分布及 KL divergence 来检测 m⁷G46。；m⁷G46 引起附近电流信号畸变，影响邻位 U47 的预测；这不是 G46 的直接 Ψ 调用。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 通过比较 WT 与 trm8Δ 在相邻 U47 的 Ψ 概率分布及 KL divergence 来检测 m⁷G46。 | text | E1 |
| G2 | m⁷G46 引起附近电流信号畸变，影响邻位 U47 的预测；这不是 G46 的直接 Ψ 调用。 | text | E2 |

- E1：PDF 第 10 页，text。“at the neighbouring U47”
- E2：PDF 第 10 页，text。“m 7 G caused signal distortion at and around position 46”

证据边界：不得将邻位信号称为 G46 被化学特异性直接定量。

### MOD-03 — Figure 4a 横轴位置 34 和 37 的完整标签分别是什么，颜色分别是什么？若上标无法辨认请明确说明。

参考状态：`answered`。

位置 34 标签为 ncm⁵U34，5 为上标。；位置 34 标签为红色。；位置 37 标签为 m¹G37，1 为上标。；位置 37 标签为深灰黑色。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 位置 34 标签为 ncm⁵U34，5 为上标。 | visual | E1 |
| G2 | 位置 34 标签为红色。 | visual | E1 |
| G3 | 位置 37 标签为 m¹G37，1 为上标。 | visual | E2 |
| G4 | 位置 37 标签为深灰黑色。 | visual | E2 |

- E1：PDF 第 9 页，vision，Figure 4a。直接放大横轴位置 34，文字是红色的 ncm⁵U34；5 是上标。
- E2：PDF 第 9 页，vision，Figure 4a。直接放大横轴位置 37，文字是深灰黑色的 m¹G37；1 是上标。

证据边界：不得写成 mcm⁵U34 或 m⁷G37；不得把曲线颜色当标签颜色。

### MOD-04 — 请根据这份 PDF 的 Figure 99a 说明实验结果；如果不存在该图，请明确拒答，不要用其他图替代。

参考状态：`refused`。

这份 PDF 中不存在 Figure 99a，无法按该图说明实验结果。

已核查本 PDF 第 1–15 页的正文、主图、图注及附带页；没有 Figure 99 或 99a。范围只限这一份 PDF，不推断未提供的独立补充文件。

证据边界：不得编造 Figure 99a 的结果、页码或证据。

## HIST — Three decades of nanopore sequencing

DOI：10.1038/nbt.3423；文件：`ref_baseline/nbt.3423.pdf`；7 页；SHA-256：`7fc0a82fd4c17ab23fe0dacb10dd50623d012e73e372671f43251b638ec85391`。

### HIST-01 — Box 1 如何解释 nanopore sequencing 中电压、酶和离子电流各自的作用？

参考状态：`answered`。

恒定电压偏置产生离子电流，并驱动 ssDNA 或 ssRNA 从 cis 向 trans 穿过孔。；聚合酶或解旋酶控制并逐步推进核苷酸，通过电流变化读取序列信息。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 恒定电压偏置产生离子电流，并驱动 ssDNA 或 ssRNA 从 cis 向 trans 穿过孔。 | text | E1 |
| G2 | 聚合酶或解旋酶控制并逐步推进核苷酸，通过电流变化读取序列信息。 | text | E2 |

- E1：PDF 第 2 页，text。“A constant voltage bias”
- E2：PDF 第 2 页，text。“An enzyme (e.g., a polymerase or helicase)”

### HIST-02 — 早期 purine/pyrimidine 区段区分实验为什么不能直接证明已实现 individual nucleobase resolution？

参考状态：`answered`。

两类电流水平差异来源于胞嘧啶和腺嘌呤区段的螺旋结构差异及通过孔时是否需要解旋。；该实验没有分辨单个核碱基，只说明孔可提供寡聚物结构或组成信息。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 两类电流水平差异来源于胞嘧啶和腺嘌呤区段的螺旋结构差异及通过孔时是否需要解旋。 | text | E1 |
| G2 | 该实验没有分辨单个核碱基，只说明孔可提供寡聚物结构或组成信息。 | text | E2 |

- E1：PDF 第 2 页，text。“cytosine-containing portion of the molecule forms a narrow single-stranded helix”
- E2：PDF 第 2 页，text。“Even though individual nucleobases were not resolved”

证据边界：不得把区段级结构区分等同于逐碱基测序。

### HIST-03 — 只读 Figure 2 时间线：MinION 向 MAP early users 发布在哪一年？MinION alone 完成 E. coli de novo assembly 在哪一年，标注准确率是多少？

参考状态：`answered`。

MinION 向 MAP early users 发布标在 2014 年。；E. coli genome 用 MinION alone 完成 de novo assembly 标在 2015 年，accuracy 为 99.4%。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | MinION 向 MAP early users 发布标在 2014 年。 | visual | E1 |
| G2 | E. coli genome 用 MinION alone 完成 de novo assembly 标在 2015 年，accuracy 为 99.4%。 | visual | E1 |

- E1：PDF 第 2 页，vision，Figure 2。时间线 2014 下方标 ONT releases MinION to early users in the MAP program；2015 上方标 E. coli genome assembled de novo with 99.4% accuracy using MinION alone。

证据边界：不得把 99.4% 解释成未经组装的每条原始 read 准确率。

### HIST-04 — 请根据这份 PDF 的 Figure 99a 说明实验结果；如果不存在该图，请明确拒答，不要用其他图替代。

参考状态：`refused`。

这份 PDF 中不存在 Figure 99a，无法按该图说明实验结果。

已核查本 PDF 第 1–7 页的正文、主图、图注及附带页；没有 Figure 99 或 99a。范围只限这一份 PDF，不推断未提供的独立补充文件。

证据边界：不得编造 Figure 99a 的结果、页码或证据。

## HMM — Detecting DNA cytosine methylation using nanopore sequencing

DOI：10.1038/nmeth.4184；文件：`ref_baseline/nmeth.4184.pdf`；7 页；SHA-256：`97a2f61cf1c313c815ab7928f831baa2969870ae24e103428e2aa2182e90a642`。

### HMM-01 — 该研究用什么模型直接识别 5-mC，信号 emission distribution 依赖多长的 k-mer？是否需要先做 chemical treatment？

参考状态：`answered`。

使用 hidden Markov model（HMM）从 MinION 电流读出识别 5-mC。；emission distribution 以 Gaussian 分布建模，其均值与标准差依赖 6-mer。；该方法不需要 chemical treatment。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 使用 hidden Markov model（HMM）从 MinION 电流读出识别 5-mC。 | text | E1 |
| G2 | emission distribution 以 Gaussian 分布建模，其均值与标准差依赖 6-mer。 | text | E2 |
| G3 | 该方法不需要 chemical treatment。 | text | E3 |

- E1：PDF 第 1 页，text。“train a hidden Markov model to distinguish 5-mC”
- E2：PDF 第 1 页，text。“which in this case is a 6-mer”
- E3：PDF 第 1 页，text。“without any chemical treatment”

### HMM-02 — log-likelihood ratio threshold=2.5 时，R7.3 与 R9 的 accuracy 和可调用位点比例各是多少？提高 stringency 的代价是什么？

参考状态：`answered`。

R7.3：accuracy 91%，在 68% 位点作出调用。；R9：accuracy 94%，在 77% 位点作出调用。；提高调用严格程度会提高准确率，但可调用位点减少。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | R7.3：accuracy 91%，在 68% 位点作出调用。 | text | E1 |
| G2 | R9：accuracy 94%，在 77% 位点作出调用。 | text | E2 |
| G3 | 提高调用严格程度会提高准确率，但可调用位点减少。 | text | E3 |

- E1：PDF 第 2 页，text。“accuracy of 91% and made calls at 68% of sites”
- E2：PDF 第 2 页，text。“accuracy of 94% and made calls at 77% of sites”
- E3：PDF 第 2 页，text。“cost of making calls at fewer sites”

证据边界：不得混淆 accuracy 与调用覆盖率，或把不同 pore 的数值交换。

### HMM-03 — 只看 Figure 1b：绿色 PCR+MSssI 分布的主峰相对蓝色 PCR 分布在左还是右？横轴是什么量、单位是什么？

参考状态：`answered`。

绿色分布的主峰在蓝色分布主峰右侧。；横轴是 Transformed event level，单位 pA。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 绿色分布的主峰在蓝色分布主峰右侧。 | visual | E1 |
| G2 | 横轴是 Transformed event level，单位 pA。 | visual | E1 |

- E1：PDF 第 2 页，vision，Figure 1b。R7.3 AGGTMG 子图中蓝色主峰约在 51，绿色约在 53.5；横轴写 Transformed event level (pA)。

证据边界：不得从单个例子推断所有 6-mer 的甲基化均使电流增加。

### HMM-04 — 请根据这份 PDF 的 Figure 99a 说明实验结果；如果不存在该图，请明确拒答，不要用其他图替代。

参考状态：`refused`。

这份 PDF 中不存在 Figure 99a，无法按该图说明实验结果。

已核查本 PDF 第 1–7 页的正文、主图、图注及附带页；没有 Figure 99 或 99a。范围只限这一份 PDF，不推断未提供的独立补充文件。

证据边界：不得编造 Figure 99a 的结果、页码或证据。

## CHN — Composite Hedges Nanopores codec system for rapid and portable DNA data readout with high INDEL-Correction

DOI：10.1038/s41467-024-53455-3；文件：`ref_baseline/s41467-024-53455-3.pdf`；12 页；SHA-256：`83cf840b0ad5d1c98f1d9a7912f5502cc8b798e12c43f4dc256c6e583ae38e51`。

### CHN-01 — CHN 摘要报告可处理多高的 indel 和 substitution rate？采用 degenerated eight-letter alphabet 后 information density 从多少变成多少？

参考状态：`answered`。

报告可处理 indel rate 达 15.9%，substitution rate 达 7.8%。；使用退化八字母表后 overall information density 从 0.59 提高到 1.17。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 报告可处理 indel rate 达 15.9%，substitution rate 达 7.8%。 | text | E1 |
| G2 | 使用退化八字母表后 overall information density 从 0.59 提高到 1.17。 | text | E2 |

- E1：PDF 第 1 页，text。“indel rates up to 15.9% and substitution rates up to 7.8%”
- E2：PDF 第 1 页，text。“from 0.59 to 1.17”

证据边界：不得将特定实验/测试能力扩展为任意数据和误差分布下的绝对保证。

### CHN-02 — CHN 的代表性 text/image 文件分别需要多久 sequencing time；完全恢复所需 composite-strand physical redundancy 各估计多少？

参考状态：`answered`。

代表性文本与图像的测序时间分别为 20 min 和 120 min。；完全恢复所需 composite-strand physical redundancy 分别估计为文本 4×、图像 8×。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 代表性文本与图像的测序时间分别为 20 min 和 120 min。 | text | E1 |
| G2 | 完全恢复所需 composite-strand physical redundancy 分别估计为文本 4×、图像 8×。 | text | E2 |

- E1：PDF 第 1 页，text。“sequencing times of 20 and 120 minutes”
- E2：PDF 第 1 页，text。“text and image data require 4× and 8× physical redundancy”

证据边界：不得把测序时间当作包含文库制备、basecalling、解码的完整端到端时间；冗余是估计。

### CHN-03 — 只看 Figure 4b 下半部：raw 与 filtered strands 的 indel error rate 标注各是多少？substitution rate 的降幅是否比 indel 小？

参考状态：`answered`。

raw strands 的 indel rate 标为 16.67±0.47%，filtered 标为 2.66±0.19%。；substitution rate 从 4.91±0.47% 变为 4.73±0.46%，降幅比 indel 小。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | raw strands 的 indel rate 标为 16.67±0.47%，filtered 标为 2.66±0.19%。 | visual | E1 |
| G2 | substitution rate 从 4.91±0.47% 变为 4.73±0.46%，降幅比 indel 小。 | visual | E1 |

- E1：PDF 第 8 页，vision，Figure 4b。Figure 4b 下方 sub 组标 4.91±0.47%、4.73±0.46%；indel 组标 16.67±0.47%、2.66±0.19%。

证据边界：不得将图中 error rate 当作完全恢复的失败概率；不从误差棒外观推断未报告的显著性。

### CHN-04 — 请根据这份 PDF 的 Figure 99a 说明实验结果；如果不存在该图，请明确拒答，不要用其他图替代。

参考状态：`refused`。

这份 PDF 中不存在 Figure 99a，无法按该图说明实验结果。

已核查本 PDF 第 1–12 页的正文、主图、图注及附带页；没有 Figure 99 或 99a。范围只限这一份 PDF，不推断未提供的独立补充文件。

证据边界：不得编造 Figure 99a 的结果、页码或证据。

## SUS — Empowering low-crosstalk, dynamic-decision random access of DNA storage via 384-multiplexed nanopore signatures

DOI：10.1038/s41467-025-64293-2；文件：`ref_baseline/s41467-025-64293-2.pdf`；12 页；SHA-256：`fc59cfccf861f796d41ea4329fe4ff06b149947b9b49a0c7bb826b2f96eaebb4`。

### SUS-01 — SUSTag 用什么 distance 和设计策略降低 crosstalk？ORCtrL 用什么网络与 optional rejection 机制？

参考状态：`answered`。

SUSTag 设计利用 Bhattacharyya distance 和 incremental clustering 以降低标签串扰。；ORCtrL 采用 CNN-LSTM；selection module 输出 yes/no，控制是否接受 prediction。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | SUSTag 设计利用 Bhattacharyya distance 和 incremental clustering 以降低标签串扰。 | text | E1 |
| G2 | ORCtrL 采用 CNN-LSTM；selection module 输出 yes/no，控制是否接受 prediction。 | text | E2 |

- E1：PDF 第 2 页，text。“leverages Bhattacharyya distance”
- E2：PDF 第 4 页，text。“selection module, which returns binary (yes or no) results”

### SUS-02 — SUSTag-ORCtrL 摘要中的 96-plex 与 384-plex weighted F1-score 各是多少？120 min 新域数据的 domain adaptation 把性能从什么水平提高到什么水平？

参考状态：`answered`。

96-plex 的 intra-class weighted F1-score 为 99.69%，384-plex 为 99.05%。；摘要称 120 min 新测序数据（约 200k reads）用于适应新域，把性能从约 87% 提高到超过 94%。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 96-plex 的 intra-class weighted F1-score 为 99.69%，384-plex 为 99.05%。 | text | E1 |
| G2 | 摘要称 120 min 新测序数据（约 200k reads）用于适应新域，把性能从约 87% 提高到超过 94%。 | text | E2 |

- E1：PDF 第 1 页，text。“F1-score of 99.69% for 96-plex”
- E2：PDF 第 1 页，text。“boosts the model performance from 87% to over 94%”

证据边界：不得称无需新域数据；不得把 F1-score 当作目标文件完全恢复率。

### SUS-03 — 只看 Figure 2c 的三张 confusion matrix：ONT 96、Porcupine 96、SUSTag 96 各标注什么 F1-score，哪个最高？

参考状态：`answered`。

ONT 96 标注 F1-score=0.9925。；Porcupine 96 标注 F1-score=0.9891。；SUSTag 96 标注 F1-score=0.9969，三者中最高。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | ONT 96 标注 F1-score=0.9925。 | visual | E1 |
| G2 | Porcupine 96 标注 F1-score=0.9891。 | visual | E1 |
| G3 | SUSTag 96 标注 F1-score=0.9969，三者中最高。 | visual | E1 |

- E1：PDF 第 5 页，vision，Figure 2c。三个矩阵左下分别写 0.9925、0.9891、0.9969；标题依次 ONT 96、Porcupine 96、SUSTag 96。

证据边界：不得用 Figure 2d 的 0.9543/0.9852/0.9892 替代 Figure 2c。

### SUS-04 — 请根据这份 PDF 的 Figure 99a 说明实验结果；如果不存在该图，请明确拒答，不要用其他图替代。

参考状态：`refused`。

这份 PDF 中不存在 Figure 99a，无法按该图说明实验结果。

已核查本 PDF 第 1–12 页的正文、主图、图注及附带页；没有 Figure 99 或 99a。范围只限这一份 PDF，不推断未提供的独立补充文件。

证据边界：不得编造 Figure 99a 的结果、页码或证据。

## RARE — An agentic system for rare disease diagnosis with traceable reasoning

DOI：10.1038/s41586-025-10097-9；文件：`ref_baseline/s41586-025-10097-9.pdf`；23 页；SHA-256：`6656d8a752c1ff9833728a4e6fed3485aba74f6bfe34c0d282275e293be4702b`。

### RARE-01 — DeepRare 的 HPO-wise 平均 Recall@1 与第二名 Claude-3.7-Sonnet-thinking 各是多少？差值应表述为百分比还是百分点？

参考状态：`answered`。

DeepRare 平均 Recall@1 为 57.18%，Claude-3.7-Sonnet-thinking 为 33.39%。；两者相差 23.79 个百分点；这是绝对差值，不是相对提升 23.79%。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | DeepRare 平均 Recall@1 为 57.18%，Claude-3.7-Sonnet-thinking 为 33.39%。 | text | E1 |
| G2 | 两者相差 23.79 个百分点；这是绝对差值，不是相对提升 23.79%。 | text | E1 |

- E1：PDF 第 4 页，text。“Claude-3.7-Sonnet-thinking (33.39%)”

证据边界：不得将 23.79 个百分点称为相对提升 23.79%；指标仅对应 HPO-wise 基准。

### RARE-02 — DeepRare reasoning chain validation 的 95.4% 到底评价什么？抽查了多少病例，几位专家如何评分？

参考状态：`answered`。

95.4% 是病例级 reference accuracy 的平均值，不是诊断 Recall@1。；从八个数据集抽取 180 个病例，专家池共 10 位医生，每例由 3 位医生独立评价，病例分数取平均。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 95.4% 是病例级 reference accuracy 的平均值，不是诊断 Recall@1。 | text | E1 |
| G2 | 从八个数据集抽取 180 个病例，专家池共 10 位医生，每例由 3 位医生独立评价，病例分数取平均。 | text | E2 |

- E1：PDF 第 7 页，text。“average reference accuracy of 95.4%”
- E2：PDF 第 7 页，text。“A total of 180 cases were sampled randomly”

证据边界：不得把 95.4% 说成患者诊断准确率、临床获益率或专家一致诊断比例。

### RARE-03 — 只看 Figure 4d 的饼图和图例：占比最高的 failure mode 是什么，百分比和病例数各是多少？

参考状态：`answered`。

最大类别为 Reasoning weighing error（推理权重错误）。；占比为 41.0%，n=82；图中总样本为 200 个失败病例。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 最大类别为 Reasoning weighing error（推理权重错误）。 | visual | E1 |
| G2 | 占比为 41.0%，n=82；图中总样本为 200 个失败病例。 | visual | E1 |

- E1：PDF 第 7 页，vision，Figure 4d。最大紫色扇区标 41.0%；对应图例 Reasoning weighing error (n=82)；标题 Case failure mode analysis (n=200)。

证据边界：不得把该类别在 200 个失败病例中的占比说成全体诊断的错误率。

### RARE-04 — 请根据这份 PDF 的 Figure 99a 说明实验结果；如果不存在该图，请明确拒答，不要用其他图替代。

参考状态：`refused`。

这份 PDF 中不存在 Figure 99a，无法按该图说明实验结果。

已核查本 PDF 第 1–23 页的正文、主图、图注及附带页；没有 Figure 99 或 99a。范围只限这一份 PDF，不推断未提供的独立补充文件。

证据边界：不得编造 Figure 99a 的结果、页码或证据。

## ADDUCT — Current and Future Methodology for Quantitation and Site-Specific Mapping the Location of DNA Adducts

DOI：10.3390/toxics10010045；文件：`ref_baseline/toxics-10-00045.pdf`；12 页；SHA-256：`00169779d42aef883746d1257cc779f5954c629faf86957a779c0159d42f379d`。

### ADDUCT-01 — DNA adducts 的传统 LC-MS 定量流程是什么？它能否同时保留 genome 上的 site-specific location？

参考状态：`answered`。

分离 DNA，化学或酶水解释放 DNA adducts，再用 LC-MS 定量释放的核苷/碱基加合物。；该流程具有较高化学特异性，但不能提供原始序列中的位点特异性。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 分离 DNA，化学或酶水解释放 DNA adducts，再用 LC-MS 定量释放的核苷/碱基加合物。 | text | E1 |
| G2 | 该流程具有较高化学特异性，但不能提供原始序列中的位点特异性。 | text | E2 |

- E1：PDF 第 2 页，text。“liberate the DNA adducts from DNA by chemical means or enzyme hydrolysis”
- E2：PDF 第 3 页，text。“chemical specificity but no site-specificity”

证据边界：不得声称传统水解后 LC-MS 可以同时追溯完整基因组位点。

### ADDUCT-02 — 这篇综述是否认为 nanopore DNA adduct 测量的 chemical specificity 已达到 mass spectrometry？未来还需验证哪些测量性能？

参考状态：`answered`。

综述明确称当时 nanopore 单分子 DNA 测序技术尚未达到质谱的化学特异性。；技术仍在实施阶段，需要评价并建立 chemical specificity、sensitivity 和 accuracy。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 综述明确称当时 nanopore 单分子 DNA 测序技术尚未达到质谱的化学特异性。 | text | E1 |
| G2 | 技术仍在实施阶段，需要评价并建立 chemical specificity、sensitivity 和 accuracy。 | text | E2 |

- E1：PDF 第 7 页，text。“do not reach the chemical specificity obtained by mass spectrometry”
- E2：PDF 第 7 页，text。“chemical specificity, sensitivity, and accuracy”

证据边界：这是 2022 年综述的时间范围，不得据此断言 2026 年所有工具仍无变化。

### ADDUCT-03 — 只看 Figure 1：Position 横轴从左向右递增还是递减？最高红点位于 1000 刻度的哪一侧？

参考状态：`answered`。

横轴从左向右递减，标注依次约为 4000、3000、2000、1000、0。；最高红点在 1000 刻度右侧，即小于 1000 的位置区间。

| 主张 | 参考陈述 | 来源 | 证据 |
|---|---|---|---|
| G1 | 横轴从左向右递减，标注依次约为 4000、3000、2000、1000、0。 | visual | E1 |
| G2 | 最高红点在 1000 刻度右侧，即小于 1000 的位置区间。 | visual | E1 |

- E1：PDF 第 4 页，vision，Figure 1。Position 横轴是倒序；尖峰在 1000 刻度和 0 刻度之间。仅看此图不能精确读出 G640，640 来源于图注。

证据边界：不得用图注 G640 冒充从横轴精确读出的坐标；不得把横轴误读成正序。

### ADDUCT-04 — 请根据这份 PDF 的 Figure 99a 说明实验结果；如果不存在该图，请明确拒答，不要用其他图替代。

参考状态：`refused`。

这份 PDF 中不存在 Figure 99a，无法按该图说明实验结果。

已核查本 PDF 第 1–12 页的正文、主图、图注及附带页；没有 Figure 99 或 99a。范围只限这一份 PDF，不推断未提供的独立补充文件。

证据边界：不得编造 Figure 99a 的结果、页码或证据。

