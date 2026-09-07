# 文献分析报告

## 1. 基本信息
- 标题：Empowering low-crosstalk, dynamic decision random access of DNA storage via 384-multiplexed nanopore signatures
- 作者：未明确说明（仅见通讯邮箱 liy37@sustech.edu.cn）
- 发表平台：Nature Communications
- 年份：2025

## 2. 摘要式总结
> 这篇论文主要研究DNA 存储需要按需、准确地操纵 DNA 标签以实现随机访问；现有基于 PCR 扩增或磁珠提取的目标检索方法依赖 Watson-Crick 碱基配对与预定义引物，限制了测序过程中的动态决策能力。纳米孔测序速度约 420 bp/s，要求模型在数百毫秒内对 DNA 链分类并作出保留/拒绝决策，且需达到足够精度（如 F1-score > 0.95）以保证数据检索纯度（S2, S4）。。
> 核心方法是SUSTag 分子标签设计（基于 scrappie v1.4.2 模拟电信号，穷举 k-mer（k=5）组合，DTW 计算欧氏或 Bhattacharyya 距离矩阵，最大化 Bhattacharyya 距离与增量聚类以最小化串扰）结合 ORCtrL 深度学习模型（CNN-LSTM 骨干 + 多输出头的预测与选择/可选拒绝结构，受迁移学习启发以增强对信号变异的适应能力）（S2, Figure 1, Figure 2）。。
> 主要结果表明领域自适应使模型性能从 87% 提升至 94% 以上，并在 10 分钟至 3 小时内以极小串扰完全恢复目标数据（S3）；SUSTag 96 与 SUSTag 384 的串扰显著低于 ONT 96 与 Porcupine 96（Figure 3）；对 384 个地址位的访问率在领域自适应后显著提升（Figure 3）；所提方法在访问纯度、目标序列解码率与数据富集方面随时间优于 Readfish 与 Porcupine（Figure 4）。。

## 3. 研究问题
### 3.1 背景
提出 SUSTag 分子标签设计：基于 scrappie（v1.4.2）模拟电信号，穷举 k-mer（k=5）组合生成候选序列，使用 Dynamic Time Warping（DTW）计算欧氏距离或 Bhattacharyya 距离矩阵，并通过最大化 Bhattacharyya 距离与增量聚类降低标签间串扰。

### 3.2 论文要解决的问题
DNA 存储需要按需、准确地操纵 DNA 标签以实现随机访问；现有基于 PCR 扩增或磁珠提取的目标检索方法依赖 Watson-Crick 碱基配对与预定义引物，限制了测序过程中的动态决策能力。纳米孔测序速度约 420 bp/s，要求模型在数百毫秒内对 DNA 链分类并作出保留/拒绝决策，且需达到足够精度（如 F1-score > 0.95）以保证数据检索纯度（S2, S4）。

## 4. 方法
### 4.1 方法概述
SUSTag 分子标签设计（基于 scrappie v1.4.2 模拟电信号，穷举 k-mer（k=5）组合，DTW 计算欧氏或 Bhattacharyya 距离矩阵，最大化 Bhattacharyya 距离与增量聚类以最小化串扰）结合 ORCtrL 深度学习模型（CNN-LSTM 骨干 + 多输出头的预测与选择/可选拒绝结构，受迁移学习启发以增强对信号变异的适应能力）（S2, Figure 1, Figure 2）。

### 4.2 关键模块
- 提出 SUSTag 分子标签设计：基于 scrappie（v1.4.2）模拟电信号，穷举 k-mer（k=5）组合生成候选序列，使用 Dynamic Time Warping（DTW）计算欧氏距离或 Bhattacharyya 距离矩阵，并通过最大化 Bhattacharyya 距离与增量聚类降低标签间串扰。
- 提出 ORCtrL 深度学习模型：以 CNN-LSTM 为骨干网络，配合多个输出头构成预测与选择结构的可选拒绝模块；覆盖参数（coverage）可在训练中调节，较低覆盖率通常带来更高精度与更低串扰。
- 在 384 重（384-multiplexed）纳米孔签名上实现随机访问：不依赖预定义引物的动态决策，可在测序过程中实时执行保留或拒绝（keep-or-reject）判定。
- 领域自适应：使用约 120 分钟新测序数据（约 200k reads）即可将模型性能从 87% 提升至 94% 以上；目标数据在 10 分钟至 3 小时测序内被完全恢复，且串扰极小。
- 性能基准：在硅片（in silico）评估中比较 ONT 96、Porcupine 96 与 SUSTag 96 标签集，使用欧氏距离与 Bhattacharyya 距离矩阵及小提琴图统计（N=200 随机采样标签对）展示最小距离。
- SUSTag 96 与 SUSTag 384 的串扰显著低于 ONT 96 与 Porcupine 96，且两者的错误模式相似。
- 实验将三种标签设计（ONT 96、Porcupine 96、SUSTag 96）构建于同一序列结构中（含引物序列与质粒 pCDB180 片段），用 ORCtrL 训练目标覆盖率为 0.95，并与 CNN（Porcupine）、CNN、CNN-LSTM 等方法对比精度与召回率。
- 随机访问性能随时间比较：与 Readfish、Porcupine 方法对比 10 分钟至 3 小时测序数据的解码结果、访问纯度（access purity）变化、目标序列解码率变化及测序数据富集性能（N=14 目标组条码 #29–#42，N=370 非目标组）。
- 背景约束：纳米孔测序速度约 420 bp/s，要求模型在数百毫秒内完成单条 DNA 链的分类并作出保留/拒绝决策，且需达到足够精度（如 F1-score > 0.95）以保证数据检索纯度。
- 可行性扩展：作者主张 SUSTag 设计方法不限定标签数量与孔模型，可迁移至 R10 孔模型（如借助 seq2squiggle 对 R10.4.1 流式细胞的信号模拟），并指出未来需降低软件延迟、通过量化或剪枝优化推理速度、扩展到 PromethION 等高通量平台并应对复杂生物样本背景。
- 局限与工程挑战包括：软件延迟仍需进一步降低、模型架构需优化以适应更快推理、需扩展实时流水线以处理高通量测序数据洪流、并在复杂天然生物样本的噪声背景下保持性能。

### 4.3 创新点
以纳米孔电信号签名作为寻址信息（addressing information）对 DNA 存储进行随机访问 SUSTag：基于 Bhattacharyya 距离与增量聚类的分子标签设计，系统性地最小化标签间串扰 ORCtrL：带可选拒绝模块的 CNN-LSTM 结构，通过可调覆盖率在精度与召回/覆盖之间权衡，降低串扰 支持 384 重标签并行识别与测序过程中的动态保留/拒绝决策 仅需约 120 分钟新领域数据（约 200k reads）即可完成领域自适应

## 5. 实验与结果
### 5.1 实验设置
在纳米孔测序（R9.4.1 流式细胞）上进行实时随机访问实验，ORCtrL 训练目标覆盖率为 0.95；对比方法包括 Readfish、Porcupine 以及 CNN（Porcupine）、CNN、CNN-LSTM；测序时长设置 10 分钟、30 分钟、1 小时、3 小时等；在硅片评估中对每个 96 重标签集随机采样 N=200 对标签进行距离统计（S3, Figure 1, Figure 2, Figure 4）。

涉及数据集：比较的标签集：ONT 96、Porcupine 96、SUSTag 96、SUSTag 384；实验序列结构含 SUSTag 及其他标签、引物序列与质粒 pCDB180 片段；领域自适应使用约 120 分钟新测序数据（约 200k reads）；富集统计分组为 N=14 目标组（条码 #29–#42）与 N=370 非目标组（Figure 2, Figure 3, Figure 4）。。

### 5.2 主要结果
领域自适应使模型性能从 87% 提升至 94% 以上，并在 10 分钟至 3 小时内以极小串扰完全恢复目标数据（S3）；SUSTag 96 与 SUSTag 384 的串扰显著低于 ONT 96 与 Porcupine 96（Figure 3）；对 384 个地址位的访问率在领域自适应后显著提升（Figure 3）；所提方法在访问纯度、目标序列解码率与数据富集方面随时间优于 Readfish 与 Porcupine（Figure 4）。

### 5.3 与基线对比
- Figure 1：比较对象包括 ONT 96, Porcupine 96, SUSTag 96, 8-mers / 9-mers / 17-mers / 34-mers 设计阶段；主要观察为 a 面板展示从 Texts, images 等数字内容到 Synthesized DNA strands，再经 Nanopore targeted sequencing with signatures 与 Random access 的流程；Address bits 为橙色矩形，Information bits 为灰色矩形，电流轨迹中对应区段以橙色突出。
- Figure 3：比较对象包括 Plasmid Sequences vs Synthetic Sequences, ONT 96, Porcupine 96, SUSTag 96, SUSTag 384, W/o domain adaptation, Increasing data amount (equalized), Increasing sequencing time (inequalized), ORCtrL w/o domain adaptation vs ORCtrL with optimized domain adaptation；主要观察为 a 面板显示从 Plasmid Sequences 到 Synthetic Sequences 的 Domain adaptation，并标出 23 nt、34 nt SUSTag 384、175 nt Payload、11 nt 的片段布局。
- Figure 4：比较对象包括 Readfish, Porcupine, proposed method, 10 min vs 1 h（a/b）, 10 min vs 30 min vs 1 h vs 3 h（c）, target group N = 14（barcodes #29 到 #42）, non-target group N = 370（仅见 caption 文字）；主要观察为 页面截图中未出现 Figure 4 图形本体，a–g 各面板的曲线、柱状图或示意图均不可见，无法提取图中数值。

### 5.4 作者结论
领域自适应使模型性能从 87% 提升至 94% 以上，并在 10 分钟至 3 小时内以极小串扰完全恢复目标数据（S3）；SUSTag 96 与 SUSTag 384 的串扰显著低于 ONT 96 与 Porcupine 96（Figure 3）；对 384 个地址位的访问率在领域自适应后显著提升（Figure 3）；所提方法在访问纯度、目标序列解码率与数据富集方面随时间优于 Readfish 与 Porcupine（Figure 4）。

## 6. 图表分析
### 6.1 关键图表
- Figure 1：Fig. 1 | Design of low-crosstalk molecular tags featured with nanopore signatures as addressing information for DNA stor
- Figure 2：Fig. 2 | Experimental benchmarking of tag designs and deep-learning classifiers. a Sequence structure containing SUSTag
- Figure 3：Fig. 3 | Domain adaptation for DNA storage application. a Illustration of address bits (barcodes) for DNA information st
- Figure 4：Fig. 4 | Adaptive nanopore sequencing based random access in DNA storage. a Decoding results of PCR-free random-access d

### 6.2 图中结论
- Figure 1：作者声称 SUSTag 标签通过 Bhattacharyya 距离、距离矩阵筛选与增量聚类获得更高签名间距/更低串扰，可作为 DNA storage 的寻址信息，并支持 96 到 384 的多重扩展；该表述是作者基于图 1 的设计与基准比较所得结论，不是单一图内直接事实。
- Figure 2：caption 声称该图涉及 Experimental benchmarking of tag designs and deep-learning classifiers；具体作者结论在缺少正文引用与图形本体时不足以判断。
- Figure 3：作者声称 domain adaptation 可提升 ORCtrL/SUSTag 分类与随机访问特异性：适配数据量或 New sequencing+training 可提高 Weighted F1-score，optimized domain adaptation 相比 w/o domain adaptation 能降低非目标 SUSTag 的 access ratio、抑制串扰；这是作者结论而非图内单一数值事实。
- Figure 4：结合论文题目与 caption，作者声称提出 adaptive/dynamic-decision random access 方法，可在纳米孔测序中实现低串扰、随时间提升 access purity 与 target decoded ratio 的随机访问；但由于 Figure 4 图形本体缺失，具体作者结论不能由当前证据核验。

### 6.3 图文一致性
- Figure 1：图文基本一致：e/f 的数值标签与 c/d 的色阶方向共同支持“SUSTag 96 的距离大于 ONT 96 与 Porcupine 96”的判断；b 的流程文字支持从短 k-mer 组合筛选到 34-mers 的路径。但图中未见误差线或显著性标记，且 384 相对 96 的扩展性能不能仅由本图直接核验。（置信度：高）
- Figure 2：证据不足：没有可见图形、没有可靠 referenced_text_spans，仅有 caption 摘要与解析失败记录，无法支撑任何图文一致性判断。（置信度：不足以判断）
- Figure 3：图文总体一致：c/d 的 F1 平台标注、e 的 precision-recall 轨迹、f/g 中 Non-target 黄柱减少均支持 domain adaptation 改善访问特异性。但图中未见显著性检验标记或误差线，f/g 的 Target/Non-target 精确分界 ID 未标明，故统计显著性与阈值边界不能仅凭本图确认。（置信度：高）
- Figure 4：证据不足：当前只有 Figure 4 图注文字，没有 direct_evidence 中的图形观察，无法判断 a–g 是否支撑“proposed method 优于 Readfish/Porcupine”或随时间改善的结论。（置信度：低）

## 7. 事实检查
### 7.1 总体结论
19 条主张中：supported 5 条（text-4、text-5、text-10、text-13、figure-16、figure-18），partially_supported 9 条（text-1、text-2、text-3、text-6、text-7、text-8、text-9、text-12、text-14、text-15），unverifiable 3 条（text-11、figure-17、figure-19）。核心方法框架（SUSTag、ORCtrL、384 重复用、领域自适应 87%→94%+）有正文 S2/S3 与 Figure 1/3 的较强支持；主要薄弱点在于：(1) text-2/text-14 中的 k=5 穷举与 DTW 细节与 Figure 1 所示 8-mers/9-mers 流程不符且无证据；(2) Figure 2 与 Figure 4 图形本体缺失，导致与 Readfish/Porcupine 的优越性比较及实验基准细节只能依赖图注，无法核验；(3) text-11 的 R10/seq2squiggle/PromethION 等扩展性表述在现有材料中无任何对应证据。涉及显著性（'显著低于'）的表述缺乏统计检验证据，宜弱化为描述性结论。

### 7.2 逐项核验
- **text-1｜部分支持**：本文提出了一种用于 DNA 存储动态随机访问的方法：通过 Bhattacharyya 距离与增量聚类增强的分子标签设计（SUSTag）降低标签间串扰，并结合可选拒绝的 CNN-LSTM 深度学习模型（ORCtrL，受迁移学习启发）提升对信号变异的适应能力。该方法支持 384 重纳米孔信号签名复用，仅用约 120 分钟新测序数据（约 20 万条 reads）进行领域自适应即可将模型性能从 87% 提升至 94% 以上，并在 10 分钟至 3 小时内以低串扰完全恢复目标数据，优于 Readfish 与 Porcupine 等随机访问方法。
  - 依据：method（S2）: 'Our framework combines SUSTag, a Bhattacharyya distance and incremental clustering enhanced molecular tag design (SUSTag) to minimize crosstalk, with an Optional-Reject Cnn-lstm deep learning model inspired by TRansfer-Learning；experimental_setup（S3）: 'Domain adaptation using only 120 minutes of new sequencing data (~200k reads) boosts the model performance from 87% to over 94%, achieving complete recovery of target data with minimal crosstalk in 10 min to 3 h'；Figure 3（SUSTag 384、领域自适应 F1 由约 0.87 升至约 0.94 平台）；Figure 4 caption（与 Readfish、Porcupine 对比的自适应纳米孔随机访问）
  - 证据 ID：S2、S3、Figure 3、Figure 4
  - 说明：SUSTag（Bhattacharyya 距离+增量聚类）与 ORCtrL（CNN-LSTM、迁移学习启发）的方法框架、384 重复用（SUSTag 384）、120 分钟/~200k reads 领域自适应将性能从 87% 提升至 94% 以上、10 分钟至 3 小时完全恢复目标数据，均由 S2、S3 及 Figure 3 直接支持。但“优于 Readfish 与 Porcupine”这一比较性结论所需的 Figure 4 图形本体缺失，仅图注确认进行了三方对比，无法直接核验优异性，故整体为部分支持。
- **text-2｜部分支持**：提出 SUSTag 分子标签设计：基于 scrappie（v1.4.2）模拟电信号，穷举 k-mer（k=5）组合生成候选序列，使用 Dynamic Time Warping（DTW）计算欧氏距离或 Bhattacharyya 距离矩阵，并通过最大化 Bhattacharyya 距离与增量聚类降低标签间串扰。
  - 依据：Figure 4 referenced_text_spans: 'Methods SUSTag design algorithm We started from using the scrappie tool (v1.4.2) from Oxford Nanopore Technology (ONT) to simulate the electrical signatures from DNA sequences'；method（S2）: 'Bhattacharyya distance and incremental clustering enhanced molecular tag design (SUSTag)'；Figure 1 b: 'Bhattacharyya distance calculation'、'Distance matrix'、'Incremental clustering'、'A: 8-mers (65,536) Best 400'、'B: 9-mers (262,144) Best 400'
  - 证据 ID：S2、Figure 1、Figure 4
  - 说明：scrappie v1.4.2 模拟电信号、Bhattacharyya 距离与增量聚类降低串扰有证据（S2 及 Figure 4 页的 Methods 片段、Figure 1 b）。但“穷举 k-mer（k=5）组合”与现有证据冲突：Figure 1 b 的 pipeline 显示从 8-mers（65,536）与 9-mers（262,144）起步，未见 k=5；“使用 DTW 计算距离矩阵”在现有材料中无任何对应表述。因此关键设计细节仅有部分支持。
- **text-3｜部分支持**：提出 ORCtrL 深度学习模型：以 CNN-LSTM 为骨干网络，配合多个输出头构成预测与选择结构的可选拒绝模块；覆盖参数（coverage）可在训练中调节，较低覆盖率通常带来更高精度与更低串扰。
  - 依据：method（S2）: 'an Optional-Reject Cnn-lstm deep learning model inspired by TRansfer-Learning (ORCtrL)'；Figure 4 referenced_text_spans: 'ORCtrL offers the flexibility to adjust the optional rejection module. This allows the coverage parameter to be tuned during training, with lower coverage typically resulting in hi...'
  - 证据 ID：S2、Figure 4
  - 说明：CNN-LSTM 骨干、ORCtrL 名称与迁移学习启发由 S2 直接支持；coverage 参数可在训练中调节、较低覆盖率通常带来更高精度由 Figure 4 页引用的正文片段直接支持。但“多个输出头构成预测与选择结构”的多头架构细节在现有材料中无证据，故判为部分支持。
- **text-4｜有证据支持**：在 384 重（384-multiplexed）纳米孔签名上实现随机访问：不依赖预定义引物的动态决策，可在测序过程中实时执行保留或拒绝（keep-or-reject）判定。
  - 依据：method（S2）: 基于预定义引物的方法 'limiting dynamic decision-making whilst sequencing'，反衬本框架支持测序中动态决策；results（S4）: 'the ability to classify a DNA strand and make a keep-or-reject decision in hundreds of milliseconds'；Figure 3 a/b: 'SUSTag 384' 地址片段与 cross-talk ratio 分布；Figure 4 caption: 'Adaptive nanopore sequencing based random access in DNA storage'
  - 证据 ID：S2、S4、Figure 3、Figure 4
  - 说明：384 重签名由 Figure 3 中 SUSTag 384 与 Figure 1 pipeline 的 'Best 96 / 384' 支持；测序中 keep-or-reject 动态判定由 S4 直接支持；不依赖预定义引物由 S2 对现有 PCR/磁珠方法的批评间接支持（本文框架正是为克服该限制）。各要素均有对应证据。
- **text-5｜有证据支持**：领域自适应：使用约 120 分钟新测序数据（约 200k reads）即可将模型性能从 87% 提升至 94% 以上；目标数据在 10 分钟至 3 小时测序内被完全恢复，且串扰极小。
  - 依据：experimental_setup（S3）: 'Domain adaptation using only 120 minutes of new sequencing data (~200k reads) boosts the model performance from 87% to over 94%, achieving complete recovery of target data with minimal crosstalk in 10 min to 3 h'；Figure 3 c: Weighted F1-score 平台约 0.9456；Figure 3 d: New sequencing+training 下 F1 由约 0.87 升至约 0.9410 平台
  - 证据 ID：S3、Figure 3
  - 说明：S3 逐字支持 120 分钟、~200k reads、87%→94%+、10 分钟至 3 小时完全恢复且串扰极小；Figure 3 c/d 的曲线数值（0.87→0.9410/0.9456）与之一致，证据直接且充分。
- **text-6｜部分支持**：性能基准：在硅片（in silico）评估中比较 ONT 96、Porcupine 96 与 SUSTag 96 标签集，使用欧氏距离与 Bhattacharyya 距离矩阵及小提琴图统计（N=200 随机采样标签对）展示最小距离。
  - 依据：Figure 1 c/d: ONT 96、Porcupine 96、SUSTag 96 的 Euclidian 与 Bhattacharyya 距离矩阵（色标 0–4 与 0–50）；Figure 1 e/f: 三组标签的 Euclidian（2.02/2.88/4.02）与 Bhattacharyya（15.42/25.66/35.22）距离分布图
  - 证据 ID：Figure 1
  - 说明：三标签集的欧氏/Bhattacharyya 距离矩阵与分布（小提琴样式）图由 Figure 1 c–f 直接支持，SUSTag 96 距离最高。但“in silico 评估”“N=200 随机采样标签对”“最小距离”等统计设定在现有图内可见文字与正文摘录中均未出现，无法核验，故为部分支持。
- **text-7｜部分支持**：SUSTag 96 与 SUSTag 384 的串扰显著低于 ONT 96 与 Porcupine 96，且两者的错误模式相似。
  - 依据：Figure 3 b: ONT 96、Porcupine 96 的 cross-talk ratio 分布更宽且偏高；SUSTag 96 与 SUSTag 384 更靠近低值且更窄
  - 证据 ID：Figure 3
  - 说明：Figure 3 b 直接显示 SUSTag 96 与 SUSTag 384 的 cross-talk ratio 分布更低更窄，支持“串扰更低”；但图中未见显著性检验标记或误差线，“显著”一词的强度缺乏统计证据。另外“两者的错误模式相似”在现有材料中无对应证据。故为部分支持。
- **text-8｜部分支持**：实验将三种标签设计（ONT 96、Porcupine 96、SUSTag 96）构建于同一序列结构中（含引物序列与质粒 pCDB180 片段），用 ORCtrL 训练目标覆盖率为 0.95，并与 CNN（Porcupine）、CNN、CNN-LSTM 等方法对比精度与召回率。
  - 依据：Figure 2 caption: 'Fig. 2 | Experimental benchmarking of tag designs and deep-learning classifiers. a Sequence structure containing SUSTag...'；Figure 2 metrics_or_axes: precision、recall；Figure 2 compared_items: '. Recall for classifying three types of barcode designs usin...'
  - 证据 ID：Figure 2
  - 说明：Figure 2 图注确认该图包含标签序列结构与三种条码设计分类的精度/召回率基准，方向上与主张一致。但 Figure 2 图形本体视觉解析失败（ReadTimeout），且“质粒 pCDB180 片段”“目标覆盖率 0.95”等具体数值在现有材料中均未出现（规则预检查亦提示 180 无出处），这些细节无法核验。
- **text-9｜部分支持**：随机访问性能随时间比较：与 Readfish、Porcupine 方法对比 10 分钟至 3 小时测序数据的解码结果、访问纯度（access purity）变化、目标序列解码率变化及测序数据富集性能（N=14 目标组条码 #29–#42，N=370 非目标组）。
  - 依据：Figure 4 caption: a Readfish、b Porcupine（10 min 与 1 h PCR-free 解码）；c proposed method（10 min、30 min、1 h、3 h）；d Access purity changes over time for the three methods；e Target sequences decoded ratio changes over time；f Sequencing data enrichm；Figure 4 caption 可见 N = 14（target group, barcodes #29 到 #42）与 N = 370（non-target group）字样
  - 证据 ID：Figure 4
  - 说明：图注确认了与 Readfish、Porcupine 三方法随时间的 access purity、target decoded ratio、数据富集对比及 N=14（#29–#42）/N=370 的统计设定，与主张所列项目和样本量一致。但 Figure 4 图形本体完全缺失，实际的解码结果数值与富集性能无法核验；且主张描述偏结果性，图注只能确认对比框架存在，故为部分支持。
- **text-10｜有证据支持**：背景约束：纳米孔测序速度约 420 bp/s，要求模型在数百毫秒内完成单条 DNA 链的分类并作出保留/拒绝决策，且需达到足够精度（如 F1-score > 0.95）以保证数据检索纯度。
  - 依据：results（S4）: 'the ability to classify a DNA strand and make a keep-or-reject decision in hundreds of milliseconds (due to the sequencing speed of ~420 bp/s) with sufficient accuracy (e.g., F1-score > 0.95) to ensure data retrieval purity'
  - 证据 ID：S4
  - 说明：S4 逐字包含 420 bp/s、数百毫秒 keep-or-reject 决策、F1-score > 0.95 保证检索纯度的全部要素，证据直接且充分。
- **text-11｜无法核验**：可行性扩展：作者主张 SUSTag 设计方法不限定标签数量与孔模型，可迁移至 R10 孔模型（如借助 seq2squiggle 对 R10.4.1 流式细胞的信号模拟），并指出未来需降低软件延迟、通过量化或剪枝优化推理速度、扩展到 PromethION 等高通量平台并应对复杂生物样本背景。
  - 依据：Figure 4 compared_items: 'a noisy and variable back- ground. Overcoming these challeng...'（仅暗示复杂背景挑战，无 R10/seq2squiggle/PromethION/量化剪枝表述）
  - 证据 ID：Figure 4
  - 说明：现有正文摘录（S1–S5）与图表证据中均未出现“R10”“R10.4.1”“seq2squiggle”“PromethION”“量化/剪枝”“软件延迟”等表述；唯一相关线索是 Figure 4 页面中“noisy and variable background. Overcoming these challenges...”的残句，不足以支持该扩展性主张的具体内容，整体无法核验。
- **text-12｜部分支持**：局限与工程挑战包括：软件延迟仍需进一步降低、模型架构需优化以适应更快推理、需扩展实时流水线以处理高通量测序数据洪流、并在复杂天然生物样本的噪声背景下保持性能。
  - 依据：Figure 4 compared_items: 'a noisy and variable back- ground. Overcoming these challeng...'；results（S4）: 数百毫秒决策时限（间接说明推理速度的工程压力）
  - 证据 ID：S4、Figure 4
  - 说明：“复杂噪声背景下保持性能”可由 Figure 4 页面的 'a noisy and variable background. Overcoming these challenges' 残句部分支持；推理速度压力可由 S4 的数百毫秒决策要求间接印证。但“软件延迟”“模型架构优化”“扩展实时流水线以应对高通量数据洪流”等具体局限表述在现有材料中无直接证据，故为部分支持。
- **text-13｜有证据支持**：DNA 存储需要按需、准确地操纵 DNA 标签以实现随机访问；现有基于 PCR 扩增或磁珠提取的目标检索方法依赖 Watson-Crick 碱基配对与预定义引物，限制了测序过程中的动态决策能力。纳米孔测序速度约 420 bp/s，要求模型在数百毫秒内对 DNA 链分类并作出保留/拒绝决策，且需达到足够精度（如 F1-score > 0.95）以保证数据检索纯度（S2, S4）。
  - 依据：method（S2）: 'contemporary methods for targeted retrieval using PCR amplification or bead-based extraction, rely on Watson-Crick base pairing and pre-defined primers, limiting dynamic decision-making whilst sequencing'；abstract（S1）: 'accurate and on-demand manipulation of DNA tags is the highway to success in ... data storage'；results（S4）: 420 bp/s、数百毫秒、F1-score > 0.95 要求
  - 证据 ID：S1、S2、S4
  - 说明：主张标注的 S2 与 S4 均直接包含对应原文：S2 支持 PCR/磁珠方法依赖 Watson-Crick 配对与预定义引物并限制动态决策；S4 支持 420 bp/s、数百毫秒决策与 F1>0.95 的纯度要求；“按需准确操纵 DNA 标签”由 S1 支持。引证与内容一致，证据充分。
- **text-14｜部分支持**：SUSTag 分子标签设计（基于 scrappie v1.4.2 模拟电信号，穷举 k-mer（k=5）组合，DTW 计算欧氏或 Bhattacharyya 距离矩阵，最大化 Bhattacharyya 距离与增量聚类以最小化串扰）结合 ORCtrL 深度学习模型（CNN-LSTM 骨干 + 多输出头的预测与选择/可选拒绝结构，受迁移学习启发以增强对信号变异的适应能力）（S2, Figure 1, Figure 2）。
  - 依据：method（S2）: SUSTag 与 ORCtrL 框架、CNN-LSTM、迁移学习启发；Figure 4 referenced_text_spans: 'Methods SUSTag design algorithm We started from using the scrappie tool (v1.4.2)...'；Figure 1 b: Bhattacharyya distance、Distance matrix、Incremental clustering、8-mers/9-mers pipeline
  - 证据 ID：S2、Figure 1、Figure 4
  - 说明：scrappie v1.4.2、Bhattacharyya 距离、增量聚类、ORCtrL（CNN-LSTM + 迁移学习）均有证据。但“k=5 穷举 k-mer”与 Figure 1 所示 8-mers/9-mers 起点不符且无其他证据；“DTW”“多输出头预测与选择结构”在现有材料中无证据；引用的 Figure 2 图形本体缺失。综合判定为部分支持。
- **text-15｜部分支持**：领域自适应使模型性能从 87% 提升至 94% 以上，并在 10 分钟至 3 小时内以极小串扰完全恢复目标数据（S3）；SUSTag 96 与 SUSTag 384 的串扰显著低于 ONT 96 与 Porcupine 96（Figure 3）；对 384 个地址位的访问率在领域自适应后显著提升（Figure 3）；所提方法在访问纯度、目标序列解码率与数据富集方面随时间优于 Readfish 与 Porcupine（Figure 4）。
  - 依据：experimental_setup（S3）: 120 分钟、~200k reads、87%→94%+、10 min–3 h 完全恢复；Figure 3 b: SUSTag 96/384 cross-talk ratio 更低更窄；Figure 3 f/g: w/o domain adaptation 非目标区黄色柱较多（部分约 0.2），optimized domain adaptation 后非目标柱明显减少接近 0；Figure 4 caption: 三方法 access purity、target decoded ratio、enrichment 随时间对比（图形本体缺失）
  - 证据 ID：S3、Figure 3、Figure 4
  - 说明：S3 与 Figure 3 c/d/f/g 支持领域自适应提升性能、降低非目标访问及 SUSTag 低串扰。但“显著低于”缺乏显著性检验证据；“优于 Readfish 与 Porcupine”依赖 Figure 4 的实际结果，而 Figure 4 图形本体完全不可见，仅图注确认对比存在，无法核验优越性。故为部分支持。
- **figure-16｜有证据支持**：作者声称 SUSTag 标签通过 Bhattacharyya 距离、距离矩阵筛选与增量聚类获得更高签名间距/更低串扰，可作为 DNA storage 的寻址信息，并支持 96 到 384 的多重扩展；该表述是作者基于图 1 的设计与基准比较所得结论，不是单一图内直接事实。
  - 依据：Figure 1 a: Address bits（橙色）作为寻址信息、Nanopore targeted sequencing with signatures、Random access 流程；Figure 1 b: Bhattacharyya distance calculation、Distance matrix、Incremental clustering、'34-mers (40,000) Best 96 / 384'；Figure 1 e/f: SUSTag 96 的 Euclidian（4.02）与 Bhattacharyya（35.22）距离高于 ONT 96（2.02/15.42）与 Porcupine 96（2.88/25.66）
  - 证据 ID：Figure 1
  - 说明：Figure 1 各面板直接呈现主张的设计流程（Bhattacharyya 距离、距离矩阵、增量聚类）、'Best 96 / 384' 的多重扩展，以及 c–f 中 SUSTag 96 签名间距（欧氏/Bhattacharyya 距离）高于另两组标签集的基准结果，证据直接且一致。规则预检查提示的“片段未在原文中找到”系针对正文文本检索，而本主张本就标注为基于图 1 观察的作者结论，图形证据充分。
- **figure-17｜无法核验**：caption 声称该图涉及 Experimental benchmarking of tag designs and deep-learning classifiers；具体作者结论在缺少正文引用与图形本体时不足以判断。
  - 依据：Figure 2 caption 摘要: 'Fig. 2 | Experimental benchmarking of tag designs and deep-learning classifiers. a Sequence structure containing SUSTag'；Figure 2 uncertainties: '视觉解析失败（ReadTimeout）'、'正文缺少明确引用段落'
  - 证据 ID：Figure 2
  - 说明：仅能确认 Figure 2 图注主题，图形本体因视觉解析失败而不可见，正文亦无对应引用段落，无法对图内任何具体结论进行核验。该主张本身已声明不足以判断，维持 unverifiable。
- **figure-18｜有证据支持**：作者声称 domain adaptation 可提升 ORCtrL/SUSTag 分类与随机访问特异性：适配数据量或 New sequencing+training 可提高 Weighted F1-score，optimized domain adaptation 相比 w/o domain adaptation 能降低非目标 SUSTag 的 access ratio、抑制串扰；这是作者结论而非图内单一数值事实。
  - 依据：Figure 3 c: Weighted F1-score 随 Adapted data amount 由约 0.92 升至约 0.9456 平台；Figure 3 d: New sequencing+training 下 F1 随时间由约 0.87 升至约 0.9410 平台；Figure 3 e: W/o domain adaptation 灰点位于左下，equalized/inequalized 轨迹向其右上改善；Figure 3 f vs g: optimized domain adaptation 后非目标区 Non-target 柱明显减少、接近 0
  - 证据 ID：Figure 3
  - 说明：Figure 3 多个面板直接支持该作者结论：c/d 显示适配数据量与测序+训练时间提升 Weighted F1-score；e 显示无领域自适应时点云位于左下；g 相对 f 显示优化领域自适应后非目标 SUSTag 的 access ratio 明显受抑。证据直接、多面板一致。
- **figure-19｜无法核验**：结合论文题目与 caption，作者声称提出 adaptive/dynamic-decision random access 方法，可在纳米孔测序中实现低串扰、随时间提升 access purity 与 target decoded ratio 的随机访问；但由于 Figure 4 图形本体缺失，具体作者结论不能由当前证据核验。
  - 依据：Figure 4 caption: 方法对比框架（a Readfish、b Porcupine、c proposed method、d access purity、e target decoded ratio、f enrichment）；Figure 4 direct_evidence: '所提供的页面截图中未出现 Figure 4 的图形本体（a–g 各面板的曲线、柱状图或示意图均不可见）'
  - 证据 ID：Figure 4
  - 说明：仅有 Figure 4 图注确认了三方法对比与指标框架，图形本体完全缺失，任何关于随时间提升纯度/解码率及低串扰的具体表现均无法由当前材料核验。该主张自身已限定结论不可核验，维持 unverifiable。
- **规则预检查提示**：
  - text-1：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-2：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-3：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-4：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-5：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-6：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-7：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-8：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-8：数值 180 未在原文或图表证据中出现。
  - text-9：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-10：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-11：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-11：数值 10.4 未在原文或图表证据中出现。
  - text-12：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-13：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-14：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-15：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - figure-16：证据片段未在原文中找到（可能被改写或虚构）：a 面板展示从 Texts, images 等数字内容到 Synthesized
  - figure-16：证据片段未在原文中找到（可能被改写或虚构）：b 面板左侧标有 Seq #p 与 Seq #q 的电流波形，并给出 Bhatt
  - figure-16：证据片段未在原文中找到（可能被改写或虚构）：b 面板 SUSTag design pipeline 显示：A: 8-mers
  - figure-17：证据片段未在原文中找到（可能被改写或虚构）：未获得 Figure 2 的图形本体，无法读取坐标轴、柱形/曲线数值、图例映射或
  - figure-17：证据片段未在原文中找到（可能被改写或虚构）：现有 direct_evidence 仅包含 caption 摘要与“PDF 解
  - figure-17：证据片段未在原文中找到（可能被改写或虚构）：semantic_source 为 noop 且记录视觉解析失败 ReadTim
  - figure-18：证据片段未在原文中找到（可能被改写或虚构）：a 面板显示从 Plasmid Sequences 到 Synthetic Se
  - figure-18：证据片段未在原文中找到（可能被改写或虚构）：b 面板并列 ONT 96、Porcupine 96、SUSTag 96、SUS
  - figure-18：证据片段未在原文中找到（可能被改写或虚构）：c 面板 Weighted F1-score 随 Adapted data am
  - figure-19：证据片段未在原文中找到（可能被改写或虚构）：页面截图中未出现 Figure 4 图形本体，a–g 各面板的曲线、柱状图或示意
  - figure-19：证据片段未在原文中找到（可能被改写或虚构）：可见图注说明 a、b 分别比较 Readfish 与 Porcupine 在 1
  - figure-19：证据片段未在原文中找到（可能被改写或虚构）：可见图注说明 c 为 proposed method 在 10 min、30 m

## 8. 评价
### 8.1 优点
- 低串扰：SUSTag 96/384 串扰显著低于 ONT 96 与 Porcupine 96
- 高效领域自适应：约 120 分钟新数据即可将性能从 87% 提升至 94% 以上
- 数据恢复快：目标数据在 10 分钟至 3 小时测序内完全恢复
- 可扩展性：设计方法不限定标签数量与孔模型，支持动态增量聚类定制
- 实用性能基准全面：与 Readfish、Porcupine 进行时间序列、访问纯度、解码率与富集多维对比

### 8.2 局限性
- 当前基于 R9.4.1 流式细胞，R10 迁移尚待完成
- 数据流与分类间软件延迟仍需进一步降低
- 模型推理速度需优化（量化或剪枝）
- 实时流水线尚未扩展至 PromethION 等高通量平台
- 复杂天然生物样本背景下的鲁棒性未验证

### 8.3 可复现性
{'工具与模型': 'scrappie（v1.4.2，ONT）用于信号模拟；DTW 计算距离；ORCtrL 基于 CNN-LSTM', '流式细胞': 'R9.4.1', '关键参数': 'k-mer k=5；目标覆盖率 0.95；候选序列穷举 4^8=65,536 与 4^9=262,144 组合', '对比基线': 'Readfish、Porcupine、CNN（Porcupine）、CNN、CNN-LSTM', '可用材料': 'Figure 2、Figure 3、Figure 4 提供 Source Data 文件；正文提及 Supplementary Table S2', '作者与代码可得性': '未明确说明；通讯邮箱 liy37@sustech.edu.cn'}

## 9. 启发与参考价值
### 9.1 适用场景
该方法可优先参考于与 比较的标签集：ONT 96、Porcupine 96、SUSTag 96、SUSTag 384；实验序列结构含 SUSTag 及其他标签、引物序列与质粒 pCDB180 片段；领域自适应使用约 120 分钟新测序数据（约 200k reads）；富集统计分组为 N=14 目标组（条码 #29–#42）与 N=370 非目标组（Figure 2, Figure 3, Figure 4）。 类似的数据或任务场景。

### 9.2 对当前研究的启发
以纳米孔电信号签名作为寻址信息（addressing information）对 DNA 存储进行随机访问 SUSTag：基于 Bhattacharyya 距离与增量聚类的分子标签设计，系统性地最小化标签间串扰 ORCtrL：带可选拒绝模块的 CNN-LSTM 结构，通过可调覆盖率在精度与召回/覆盖之间权衡，降低串扰 支持 384 重标签并行识别与测序过程中的动态保留/拒绝决策 仅需约 120 分钟新领域数据（约 200k reads）即可完成领域自适应

## 10. 总结
本文提出了一种用于 DNA 存储动态随机访问的方法：通过 Bhattacharyya 距离与增量聚类增强的分子标签设计（SUSTag）降低标签间串扰，并结合可选拒绝的 CNN-LSTM 深度学习模型（ORCtrL，受迁移学习启发）提升对信号变异的适应能力。该方法支持 384 重纳米孔信号签名复用，仅用约 120 分钟新测序数据（约 20 万条 reads）进行领域自适应即可将模型性能从 87% 提升至 94% 以上，并在 10 分钟至 3 小时内以低串扰完全恢复目标数据，优于 Readfish 与 Porcupine 等随机访问方法。
