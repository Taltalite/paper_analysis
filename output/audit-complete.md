# 文献分析报告

## 1. 基本信息
- 标题：Empowering low-crosstalk, dynamic-decision random access of DNA storage via 384-multiplexed nanopore signatures
- 作者：未明确说明
- 发表平台：Nature Communications
- 年份：2025

## 2. 摘要式总结
> 这篇论文主要研究DNA存储随机访问需要在纳米孔测序过程中动态识别地址位并做keep-or-reject决策；现有PCR扩增或bead-based extraction依赖Watson-Crick base pairing与预定义引物，限制了测序中的动态决策。自适应采样还要求在约420 bp/s速度下数百毫秒内分类，并具有足够准确性，原文示例阈值为F1-score > 0.95。。
> 核心方法是SUSTag：用scrappie v1.4.2模拟DNA序列电学签名，基于k=5 scrappie squiggle与实验μ/σ穷举4^8=65,536和4^9=262,144组合，DTW计算信号两两距离，可用Euclidean或Bhattacharyya distance，经距离混淆矩阵与incremental clustering完成de novo标签设计。ORCtrL：Optional-Reject CNN-LSTM deep learning model inspired by TRansfer-Learning，以CNN-LSTM backbone加多输出头构成prediction-and-selection，可训练时调节coverage参数；domain adaptation仅用120 min约200k reads新域数据。。
> 主要结果表明原文明确数值包括：domain adaptation用120 min新测序数据约200k reads，将模型性能由87%提升至超过94%，并在10 min到3 h实现complete recovery of target data with minimal crosstalk。图注称SUSTag 96与SUSTag 384的crosstalk显著低于ONT 96和Porcupine 96，error patterns相似；Fig.4给出三种方法随时间变化的access purity、target decoded ratio、富集与累计read yield，但摘录未提供具体解码率数值。。

## 3. 研究问题
### 3.1 背景
提出低串扰SUSTag标签：基于k=5 scrappie squiggle信号、DTW欧氏/Bhattacharyya距离、距离混淆矩阵与增量聚类进行de novo设计。

### 3.2 论文要解决的问题
DNA存储随机访问需要在纳米孔测序过程中动态识别地址位并做keep-or-reject决策；现有PCR扩增或bead-based extraction依赖Watson-Crick base pairing与预定义引物，限制了测序中的动态决策。自适应采样还要求在约420 bp/s速度下数百毫秒内分类，并具有足够准确性，原文示例阈值为F1-score > 0.95。

## 4. 方法
### 4.1 方法概述
SUSTag：用scrappie v1.4.2模拟DNA序列电学签名，基于k=5 scrappie squiggle与实验μ/σ穷举4^8=65,536和4^9=262,144组合，DTW计算信号两两距离，可用Euclidean或Bhattacharyya distance，经距离混淆矩阵与incremental clustering完成de novo标签设计。ORCtrL：Optional-Reject CNN-LSTM deep learning model inspired by TRansfer-Learning，以CNN-LSTM backbone加多输出头构成prediction-and-selection，可训练时调节coverage参数；domain adaptation仅用120 min约200k reads新域数据。

### 4.2 关键模块
- 提出低串扰SUSTag标签：基于k=5 scrappie squiggle信号、DTW欧氏/Bhattacharyya距离、距离混淆矩阵与增量聚类进行de novo设计。
- 提出ORCtrL模型：以CNN-LSTM为骨干，接多个输出头形成prediction-and-selection结构，并通过optional rejection/coverage参数权衡精度、召回与覆盖。
- 面向纳米孔自适应采样随机访问：需在约420 bp/s速度下数百毫秒内完成分类与keep-or-reject决策，目标示例为F1-score > 0.95。
- 报告domain adaptation收益：120 min新域测序数据约200k reads，将性能由87%提升至超过94%。
- 报告时间尺度随机访问结果：10 min、30 min、1 h、3 h测序下评估access purity、decoded ratio与富集；60 min数据按target N=14、non-target N=370统计。
- 图示比较显示SUSTag 96/384串扰低于ONT 96/Porcupine 96，但完整混淆矩阵数值未在摘录中给出。
- 局限集中于R9.4.1迁移、软件流式延迟、模型量化/剪枝推理加速、PromethION扩展与复杂天然样本鲁棒性。
- 作者、机构、完整数据可用性与部分实验参数在提供文本中未明确说明。

### 4.3 创新点
SUSTag：将纳米孔电学签名作为寻址信息并进行低串扰de novo设计 联合Bhattacharyya distance、distance confusion matrix与incremental clustering的标签生成策略 ORCtrL：CNN-LSTM骨干加optional-reject多输出头，训练期可调coverage 用少量新域数据做transfer-learning/domain adaptation以适应信号变异 面向384 address bits的自适应纳米孔随机访问演示

## 5. 实验与结果
### 5.1 实验设置
在纳米孔测序随机访问框架下评估SUSTag/ONT/Porcupine标签与ORCtrL、CNN、CNN-LSTM等分类器；ORCtrL训练目标coverage为0.95；Fig.4比较Readfish、Porcupine与本文方法在10 min、30 min、1 h、3 h下的PCR-free或随机访问解码、access purity、decoded ratio与60 min富集；Fig.3评估384 address bits在domain adaptation前后access ratios。

涉及数据集：未明确说明完整公开数据集。文中涉及标签集合：ONT 96、Porcupine 96、SUSTag 96、SUSTag 384；序列结构含SUSTag/ONT 96/Porcupine 96、引物及质粒pCDB180任意片段；随机访问统计中target组为barcodes #29到#42，N=14，non-target组N=370；domain adaptation使用约200k reads；对比方法包括Readfish与Porcupine；先验DeePlexiCon为Novoa group在DRS四组20 bp barcode结果，非本文新结果。。

### 5.2 主要结果
原文明确数值包括：domain adaptation用120 min新测序数据约200k reads，将模型性能由87%提升至超过94%，并在10 min到3 h实现complete recovery of target data with minimal crosstalk。图注称SUSTag 96与SUSTag 384的crosstalk显著低于ONT 96和Porcupine 96，error patterns相似；Fig.4给出三种方法随时间变化的access purity、target decoded ratio、富集与累计read yield，但摘录未提供具体解码率数值。

### 5.3 与基线对比
- Figure 4：比较对象包括 ORCtrl（This work）, Readfish method, Porcupine method, Non-target, Target, Channel 1-256, Channel 257-512；主要观察为 panel a（Readfish 条件）：10 minutes 与 60 minutes 下方的解码结果均为红色叉号，视觉上表示未成功解码或未达到目标。
- Figure 1：比较对象包括 ONT 96, Porcupine 96, SUSTag 96；主要观察为 panel a：展示数字内容（Texts, images, …）经 DNA 合成、带签名纳米孔靶向测序到随机访问的流程；Address bits 用橙色标识，Information bits 为灰色，纳米孔电流轨迹中对应区段以橙色突出；流程末端有绿色对勾或红色警示图标。
- Figure 3：比较对象包括 ONT 96, Porcupine 96, SUSTag 96, SUSTag 384, ORCtrL w/o domain adaptation, ORCtrL with optimized domain adaptation, Increasing data amount (equalized), Increasing sequencing time (inequalized), W/o domain adaptation；主要观察为 panel a：示意从 Plasmid Sequences 经箭头指向 Synthetic Sequences 的 domain adaptation；地址片段布局标尺为 23 nt、34 nt SUSTag 384、175 nt Payload、11 nt。
- Figure 2：比较对象包括 ONT 96（蓝色方块）, Porcupine 96（紫色三角）, SUSTag 96（橙色圆点）, CNN (Porcupine), CNN, CNN-LSTM, ORCtrl；主要观察为 panel a：线性序列结构从左到右为 Primer (23 nt)、8×T (8 nt)、三种 tag 区段（SUSTag 96 为 34 nt、Porcupine 96 为 40 nt、ONT 96 为 24 nt）、Primer (13 nt) 与 Plasmid pCDB180 (400 nt)，三种 tag 以颜色区分。

### 5.4 作者结论
原文明确数值包括：domain adaptation用120 min新测序数据约200k reads，将模型性能由87%提升至超过94%，并在10 min到3 h实现complete recovery of target data with minimal crosstalk。图注称SUSTag 96与SUSTag 384的crosstalk显著低于ONT 96和Porcupine 96，error patterns相似；Fig.4给出三种方法随时间变化的access purity、target decoded ratio、富集与累计read yield，但摘录未提供具体解码率数值。

## 6. 图表分析
### 6.1 关键图表
- Figure 4：Fig. 4 | Adaptive nanopore sequencing based random access in DNA storage. a Decoding results of PCR-free random-access d
- Figure 1：Fig. 1 | Design of low-crosstalk molecular tags featured with nanopore signatures as addressing information for DNA stor
- Figure 3：Fig. 3 | Domain adaptation for DNA storage application. a Illustration of address bits (barcodes) for DNA information st
- Figure 2：Fig. 2 | Experimental benchmarking of tag designs and deep-learning classifiers. a Sequence structure containing SUSTag

### 6.2 图中结论
- Figure 4：作者声称结论（据图注与面板标签推断）：本文提出的 ORCtrl（This work）通过 384-multiplexed nanopore signatures 实现低串扰、动态决策的随机访问，在 PCR-free 随机访问中相比 Readfish 和 Porcupine 方法具有更高的 Access purity、Target decode ratio 和更快的成功解码时间，并能通过自适应采样在测序过程中实时富集目标读段。
- Figure 1：作者声称结论（据图题推断）：SUSTag 设计流程能够生成特征距离更大的分子标签集合，SUSTag 96 相比 ONT 96 和 Porcupine 96 具有更大的欧氏距离与 Bhattacharyya 距离，即更低的地址间串扰，更适合作为 DNA 存储的寻址信息并支持 384 重多重签名。
- Figure 3：作者声称结论（据图题与面板标注推断）：域适应可将基于质粒序列训练的分类器迁移到合成序列 DNA 存储应用，优化的域适应显著提高 Weighted F1-score（可达约 0.9456）并降低非目标访问（串扰），且增加适应数据量比单纯延长测序时间更高效；SUSTag 设计本身具有更低的 cross-talk ratio。
- Figure 2：作者声称结论（据图题与面板标注推断）：SUSTag 96 是三种标签设计中分类性能最好的（F1-score 0.9969），且本文提出的 CNN-LSTM（ORCtrl 分类器核心）优于普通 CNN 与 Porcupine 的 CNN 方法，在 weighted precision–recall 上整体处于更高水平，验证了低串扰标签与可选拒绝分类器结合的有效性。

### 6.3 图文一致性
- Figure 4：证据一致性较好：panel c 的绿色对勾与 panel d、e 中 This work 曲线高位、panel f 中 ORCtrl 非目标柱更低、panel g 中 On/Off 切换下 Channel 1-256 产出响应，均与作者声称的优势方向一致。限制在于 panel a–c 缩略图内正文过小无法 OCR，panel b 黄色符号与 panel c 黑色方块含义不确定，且各图无精确数值可读，因此只能支持相对趋势层面的结论，不能验证具体量化指标。（置信度：高）
- Figure 1：证据一致性较好：panel c、d 中 SUSTag 96 矩阵颜色较浅与 panel e、f 中 SUSTag 96 距离数值最大（4.02、35.22）相互印证，直接支持“距离更大/串扰更低”的结论；panel b 的流程标签明确显示可扩展至 Best 96 / 384。限制在于 c、d 矩阵仅能通过颜色深浅作相对判断，无逐格数值；e、f 的具体分布形态（violin 细节）未在证据中详述。（置信度：高）
- Figure 3：证据一致性较好：panel c、d 的 F1-score 上升与平台标注（0.9456、0.9410）直接支持域适应有效；panel e 中 equalized 轨迹高于 inequalized 支持“增加数据量更高效”的说法；panel f 与 g 的对比直接支持优化域适应降低 Non-target 访问。限制在于 b 的图形类型（violin/density）未明确、数值均为视觉近似，且无误差线与显著性标记，统计可靠性无法从图中确认。（置信度：高）
- Figure 2：证据一致性较好：panel c 中 SUSTag 96 的 F1-score 最高（0.9969）、panel d 中 CNN-LSTM 的 F1-score 最高（0.9892）、panel e 中 CNN-LSTM 点位于右上区域，三者相互印证并与作者声称结论方向一致。限制在于 panel b 的编号网格与 Barcode 示例细节不可可靠读取，panel d 的具体任务背景（对应哪种 tag）依赖图注语境，panel c/d 色阶不完整，无法逐格验证混淆矩阵数值。（置信度：高）

### 6.4 视觉证据与解析状态
#### Figure 4
- **图注摘要：** Fig. 4 | Adaptive nanopore sequencing based random access in DNA storage. a Decoding results of PCR-free random-access d
- **图类型：** result_figure
- **视觉解析：** 已调用多模态模型（含缓存结果）
- **指标 / 坐标：** panel d: x=Time (minutes), y=Access purity, panel e: x=Time (minutes), y=Target decode ratio, panel f left: x=Avg. read counts, y=method category (Readfish/Porcupine/ORCtrl), panel f right: x=Total read counts, y=method category (Readfish/Porcupine/ORCtrl, panel g upper: y=Yield (reads / minute), x=time axis shared/not clearly labeled, panel g lower: x=Time (minutes), y=Target reads yield ratio
- **可见文字：** Readfish；CNN (Porcupine)；ORCtrl with domain adaptation；10 minutes；60 minutes；30 minutes；180 minutes；This work；Readfish method；Porcupine method；Access purity；Target decode ratio；Time (minutes)；60 Minutes；Avg. read counts；Total read counts；Non-target；Target；Random access；(adaptive sampling)；On；Off；Yield (reads / minute)；Channel 1-256
- **图例：** Non-target；Target；Channel 1-256；Channel 257-512
- **子图：** a: Readfish 条件下两张文档式解码结果缩略图，10 minutes 与 60 minutes 下方均为红色叉号，视觉上表示未成功解码/未达到目标。；b: CNN (Porcupine) 条件下两张文档式解码结果缩略图，10 minutes 与 60 minutes 下方均为黄色圆形符号，视觉上表示部分成功或中间状态。；c: ORCtrl with domain adaptation 下四张文档式结果缩略图，10/30/60/180 minutes 下方均为绿色对勾，视觉上表示各时间点均可成功解码；右侧附近有少量黑色小方块标记，含义不完全明确。；d: Access purity 随 Time (minutes) 变化；This work 星形曲线维持在接近 1.0，Readfish method 圆点曲线约 0.9 后略降，Porcupine method 三角曲线明显下降至约 0.3。；e: Target decode ratio 随 Time (minutes) 变化；This work 三角曲线接近 1.0，Porcupine method 三角曲线约 0.85–0.9，Readfish method 圆点曲线从约 0.65 升至约 0.79 后趋平。；f: 60 Minutes 下比较 Readfish、Porcupine、ORCtrl 的 Avg. read counts 与 Total read counts；橙色的 Target 与浅灰的 Non-target 成对显示，ORCtrl 的 Non-target 柱明显更低，Target 柱相对保留。；g: Random access (adaptive sampling) 的实时测序演示；上图 Yield 中 Channel 1-256 在 On 区段升高、Off 区段降低，Channel 257-512 基本维持高位；下图 Target reads yield ratio 仅在部分时间段出现尖峰。
- **不确定性：** panel a–c 中文档缩略图内的正文过小，无法可靠 OCR，只能确认标题、时间标签和状态符号。；panel b 的黄色圆形符号内部细节不够清晰，不能确定是减号、圆点还是其他状态图标。；panel c 右侧黑色小方块标记的含义无法从图中直接判定。；panel d、e、f、g 的具体数值点/柱高无法精确读取，以上只描述相对趋势。；panel g 上图的 x 轴刻度未清晰显示，时间轴可能与其下方 Target reads yield ratio 图共享。
- **证据质量：** 高
- **直接证据：**
- caption 摘要：Fig. 4 | Adaptive nanopore sequencing based random access in DNA storage. a Decoding results of PCR-free random-access d
- panel a 的 10 minutes 与 60 minutes 下方均为红色叉号，panel b 对应位置为黄色圆形符号，panel c 的四个时间点均为绿色对勾。
- panel d 中 This work 曲线位于接近 1.0 的高位，Readfish method 略低于 1.0，Porcupine method 随时间明显下降。
- panel e 中 This work 接近 1.0，Porcupine method 居中，Readfish method 从较低值上升后进入平台。
- panel f 中 ORCtrl 对应的 Non-target 柱明显短于 Readfish 与 Porcupine，而 Target 柱仍可见；图例显示灰色为 Non-target、橙色为 Target。
- panel g 上图 Channel 1-256 的橙色曲线在 On/Off 切换下呈现开高关低，Channel 257-512 灰色曲线总体维持在较高读长产出；下图橙色目标产率比只在少数时间窗出现尖峰。

#### Figure 1
- **图注摘要：** Fig. 1 | Design of low-crosstalk molecular tags featured with nanopore signatures as addressing information for DNA stor
- **图类型：** method_diagram
- **视觉解析：** 已调用多模态模型（含缓存结果）
- **指标 / 坐标：** 未明确说明
- **可见文字：** a；Texts, images, …；Synthesized DNA strands；Nanopore targeted sequencing with signatures；Random access；Address bits；Information bits；b；Bhattacharyya distance calculation；Seq #p；Seq #q；Distance matrix；Similar；Less Similar；Incremental clustering；SUSTag design pipeline；A: 8-mers (65,536) Best 400；B: 9-mers (262,144) Best 400；17-mers: A+B B+A (320,000) Best 200；34-mers (40,000) Best 96 / 384；c；Euclidian distances；ONT 96；Porcupine 96
- **图例：** 未明确说明
- **子图：** a: 展示数字内容经DNA编码、合成、带签名纳米孔靶向测序及随机访问的流程；地址位用橙色标识，测序电流中对应区段以橙色突出。；b: 展示SUSTag的从头设计流程，包括Bhattacharyya距离计算、距离矩阵、增量聚类，以及从8-mer和9-mer组合生成17-mer、再筛选34-mer的流程。；c: 并列显示ONT 96、Porcupine 96和SUSTag 96的Euclidian距离矩阵；色标范围为0至4，SUSTag矩阵整体颜色较浅。；d: 并列显示ONT 96、Porcupine 96和SUSTag 96的Bhattacharyya距离矩阵；色标范围为0至50，SUSTag矩阵整体颜色较浅。；e: 比较三种96-plex标签的Euclidian距离分布。条形数值分别为ONT 96的2.02、Porcupine 96的2.88和SUSTag 96的4.02。；f: 比较三种96-plex标签的Bhattacharyya距离分布。条形数值分别为ONT 96的15.42、Porcupine 96的25.66和SUSTag 96的35.22，横轴呈对数刻度。
- **不确定性：** b面板中Bhattacharyya距离公式的部分小字号符号在图片中较小，公式细节可能受到分辨率影响。；增量聚类图中的聚类数量及个别点的归属无法仅凭图像精确确认。
- **证据质量：** 高
- **直接证据：**
- caption 摘要：Fig. 1 | Design of low-crosstalk molecular tags featured with nanopore signatures as addressing information for DNA stor
- a面板从左至右包含数字文件、DNA双链、纳米孔测序装置、剪切符号、访问结果及绿色对勾或红色警示图标。
- a面板中Address bits为橙色矩形，Information bits为灰色矩形；纳米孔电流轨迹中的部分波动也用橙色突出。
- b面板左侧给出两条标为Seq #p和Seq #q的电流波形，并在下方列出Bhattacharyya距离公式。
- b面板中部为由深浅色块组成的Distance matrix，旁边有从Less Similar指向Similar的箭头。
- b面板右侧的Incremental clustering图中存在多个点簇及包围部分点簇的轮廓。

#### Figure 3
- **图注摘要：** Fig. 3 | Domain adaptation for DNA storage application. a Illustration of address bits (barcodes) for DNA information st
- **图类型：** multi_panel_result_figure
- **视觉解析：** 已调用多模态模型（含缓存结果）
- **指标 / 坐标：** b: 纵轴 Cross-talk ratio (%)，横轴 Normalized density, c: 纵轴 Weighted F1-score，横轴 Adapted data amount, d: 纵轴 Weighted F1-score，横轴 Time (minutes), e: 纵轴 Weighted precision，横轴 Weighted recall, f/g: 纵轴 Access ratio，横轴 SUSTag #ID
- **可见文字：** a；Domain adaptation；Plasmid Sequences；Synthetic Sequences；明德求是；日新自强；VIRTUE TRUTH ADVANCE；23 nt；34 nt；175 nt；11 nt；SUSTag 384；Payload；b；ONT 96；Porcupine 96；SUSTag 96；SUSTag 384；Cross-talk ratio (%)；Normalized density；c；Weighted F1-score；Adapted data amount；0.9456
- **图例：** 未明确说明
- **子图：** a: 示意从 Plasmid Sequences 到 Synthetic Sequences 的 domain adaptation，并给出 SUSTag 384 地址片段布局：23 nt、34 nt SUSTag 384、175 nt Payload、11 nt。；b: 四个并列的归一化密度/小提琴样式图比较 ONT 96、Porcupine 96、SUSTag 96、SUSTag 384 的 cross-talk ratio 分布；SUSTag 96 与 SUSTag 384 分布更靠近低值且更窄。；c: Weighted F1-score 随 Adapted data amount 增加而上升并趋稳，低数据量时约 0.92，平台期标注约 0.9456。；d: New sequencing+training 条件下，Weighted F1-score 在约 10 min 时约 0.87，随后快速上升，约 120–180 min 后接近平台，标注约 0.9410。；e: Weighted recall–precision 散点中，W/o domain adaptation 的灰点位于左下；Increasing data amount (equalized) 橙点向右上延伸，Increasing sequencing time (inequalized) 青点位于相对较低轨迹。；f: ORCtrL w/o domain adaptation 的 access ratio：低编号 SUSTag #ID 区域 Target 灰柱较高，约 0.8；非目标区 Non-target 有零散黄色柱，部分可达约 0.2。；g: ORCtrL with optimized domain adaptation 后，低编号 Target 灰柱仍高，约 0.8–0.9；相比 f，非目标区 Non-target 黄色柱明显更少更低，接近 0。
- **不确定性：** a 中合成序列旁的中文校训文字为艺术化小字，个别字符不宜逐字确认。；b 的图形样式在图中未明确标注为 violin 还是 density，只能按归一化密度图读取。；f/g 中 Target 与 Non-target 的精确分界 ID 未在图中标明，只能按柱色区域判断。；未在图中看到显著性检验标记或误差线，不能仅凭视觉判断统计显著性。
- **证据质量：** 高
- **直接证据：**
- caption 摘要：Fig. 3 | Domain adaptation for DNA storage application. a Illustration of address bits (barcodes) for DNA information st
- a 中从 Plasmid Sequences 经箭头指向 Synthetic Sequences，下方标尺标出 23 nt、34 nt SUSTag 384、175 nt Payload、11 nt。
- b 中 ONT 96 与 Porcupine 96 的密度分布更宽且位置偏高，SUSTag 96 与 SUSTag 384 的分布更靠近低 cross-talk ratio。
- c 中橙色点随 Adapted data amount 增加由约 0.92 升至约 0.9456 平台。
- d 中青色点随 Time (minutes) 由约 0.87 升至约 0.9410 平台。
- e 中灰点 W/o domain adaptation 位于左下，橙色 equalized 轨迹整体高于青色 inequalized 轨迹。

#### Figure 2
- **图注摘要：** Fig. 2 | Experimental benchmarking of tag designs and deep-learning classifiers. a Sequence structure containing SUSTag
- **图类型：** result_figure
- **视觉解析：** 已调用多模态模型（含缓存结果）
- **指标 / 坐标：** panels c-d: Ground truth vs Prediction 的混淆矩阵坐标轴, panel e: x 轴 Weighted recall（约 0.95–1.00），y 轴 Weighted precision（约 0.95–1.00）
- **可见文字：** a；SUSTag 96；Porcupine 96；ONT 96；(34 nt)；(40 nt)；(24 nt)；Primer (23 nt)；8×T (8 nt)；Primer (13 nt)；Plasmid pCDB180 (400 nt)；b；Optional-reject CNN-LSTM；CNN Block；LSTM Block；Conv 1D；Avg pooling；Batch Norm；×4；LSTM；Barcode 11；Barcode 36；Barcode 17；Barcode 02
- **图例：** ONT 96（蓝色方块）；Porcupine 96（紫色三角）；SUSTag 96（橙色圆点）；panel a 中以颜色区分 SUSTag 96 / Porcupine 96 / ONT 96
- **子图：** a: 线性序列结构示意，展示接头/引物、三种 tag 区段以及右侧质粒片段的相对位置与长度。；b: Optional-reject CNN-LSTM 网络结构：左侧输入类纳米孔信号波形，经 CNN Block 与四层 LSTM Block，再接多个输出头，分出 Prediction 与 Selection 两支，右侧显示 1–96 编号网格及 Recognized or not? 的 True/False 判断。；c: 三个混淆矩阵并排比较 ONT 96、Porcupine 96、SUSTag 96 的分类结果；对角线为主，SUSTag 96 的 F1-score 最高。；d: 三个混淆矩阵比较 CNN (Porcupine)、CNN、CNN-LSTM；CNN-LSTM 的 F1-score 略高于 CNN，CNN (Porcupine) 明显较低。；e: Weighted recall–Weighted precision 散点图，含 F1-score 对角虚线；同色系标记表示三种 tag 设计，ORCtrl 位于左下，CNN 居中，CNN-LSTM 位于右上，说明 CNN-LSTM 整体更靠近高精度高召回区域。
- **不确定性：** panel b 右侧 1–96 编号网格和 Barcode 示例字号过小，无法逐一可靠 OCR。；panel c/d 的混淆矩阵 colorbar 只清晰显示 0 与 0.01，完整色阶范围不能从图中确认。；panel d 是否全部对应同一 tag 设计，图中只直接显示模型名 CNN (Porcupine)、CNN、CNN-LSTM，具体任务背景依赖图注语境。；panel e 中部分 F1-score 对角虚线标签较小，0.95–0.99 可读但个别位置可能与邻近虚线混淆。
- **证据质量：** 高
- **直接证据：**
- caption 摘要：Fig. 2 | Experimental benchmarking of tag designs and deep-learning classifiers. a Sequence structure containing SUSTag
- panel a 中从左到右可见 Primer (23 nt)、8×T (8 nt)、三种 tag 区段、Primer (13 nt) 与 Plasmid pCDB180 (400 nt) 的线性排布。
- panel b 明确画出 CNN Block 内的 Conv 1D → Avg pooling → Batch Norm，并经 ×4 进入堆叠 LSTM Block。
- panel b 右侧有 Prediction 与 Selection 两个输出头，Selection 旁出现 True/False 序列与 Recognized or not? 文字。
- panel c 三个混淆矩阵下方分别标注 F1-score: 0.9925、0.9891、0.9969。
- panel d 三个混淆矩阵下方分别标注 F1-score: 0.9543、0.9852、0.9892。

## 7. 事实检查
### 7.1 总体结论
总体判定：大部分主张获得正文（S2–S4）与Figure 1–4图表证据的支持。核心框架（SUSTag+ORCtrL）、420 bp/s/数百毫秒/F1>0.95自适应采样要求、domain adaptation数值（120 min、~200k reads、87%→over 94%、10 min–3 h）均有直接证据。主要问题集中在：(1) text-2/text-11中的"k=5"与"DTW"在所提供摘录中无证据，仅Bhattacharyya/Euclidian距离与scrappie v1.4.2获证实；(2) text-6中"target N=14、non-target N=370"未出现于材料；(3) text-8所列局限点在摘录中完全无证据；(4) "显著低于""error patterns相似"等强度或附加表述超出图中可见证据（无显著性标记）；(5) text-9关于作者/机构未说明的否定性主张部分不准确（S2含sustech.edu.cn通讯邮箱）。四条figure类主张均与图表面板证据一致，判为supported。

### 7.2 逐项核验
- **text-1｜部分支持**：本文针对DNA存储中靶向检索依赖PCR扩增或bead-based extraction、受Watson-Crick base pairing与预定义引物限制、难以在测序过程中做动态keep-or-reject决策的问题，提出SUSTag分子标签设计与ORCtrL可选拒绝CNN-LSTM深度学习模型相结合的框架。SUSTag利用scrappie squiggle信号、DTW距离与增量聚类降低标签间串扰；ORCtrL通过CNN-LSTM骨干、多输出头与可调的optional rejection/coverage参数适应纳米孔信号变异。原文报告仅用120分钟新测序数据约200k reads做domain adaptation可将模型表现由87%提升至超过94%，并在10 min到3 h实现目标数据完全恢复且串扰较低；图注还称SUSTag 96/384的crosstalk显著低于ONT 96与Po
  - 依据：method（S2）："contemporary methods for targeted retrieval using PCR amplification or bead-based extraction, rely on Watson-Crick base pairing and pre-defined primers, limiting dynamic decision-making whilst sequencing. Our framework combines；experimental_setup（S3）："Domain adaptation using only 120 minutes of new sequencing data (~200k reads) boosts the model performance from 87% to over 94%, achieving complete recovery of target data with minimal crosstalk in 10 min to 3 h."；Figure 4 referenced_text_spans：coverage parameter tuned during training；Methods SUSTag design algorithm 使用 scrappie v1.4.2 模拟电学签名；Figure 3b：SUSTag 96 与 SUSTag 384 的 cross-talk ratio 分布更靠近低值
  - 证据 ID：S2、S3、Figure 3、Figure 4
  - 说明：框架动机、SUSTag+ORCtrL组合、Bhattacharyya距离与增量聚类、domain adaptation数值（120 min、~200k reads、87%→over 94%、10 min–3 h complete recovery）均有直接证据；coverage参数可调由Figure 4引用文本支持；scrappie由Methods引用文本支持。但"DTW距离"在所提供正文摘录中未出现，仅有Bhattacharyya距离证据；"crosstalk显著低于"由Figure 3b分布趋势支持但图中无显著性标记（"显著"强度被略扩大）；claim末尾截断（"Po"应为Porcupine 96）。
- **text-2｜部分支持**：提出低串扰SUSTag标签：基于k=5 scrappie squiggle信号、DTW欧氏/Bhattacharyya距离、距离混淆矩阵与增量聚类进行de novo设计。
  - 依据：method（S2）：SUSTag为"a Bhattacharyya distance and incremental clustering enhanced molecular tag design"；Figure 1b：SUSTag design pipeline，含 Bhattacharyya distance calculation、Distance matrix、Incremental clustering，8-mers (65,536)、9-mers (262,144)、17-mers、34-mers Best 96/384；Figure 4 referenced_text_spans：Methods SUSTag design algorithm 使用 scrappie v1.4.2 模拟电学签名；Figure 1c-f：ONT 96/Porcupine 96/SUSTag 96 的 Euclidian 与 Bhattacharyya 距离矩阵及分布（2.02/2.88/4.02；15.42/25.66/35.22）
  - 证据 ID：S2、Figure 1、Figure 4
  - 说明：scrappie模拟、Bhattacharyya距离、距离矩阵、增量聚类与de novo设计流程（8-mer/9-mer组合筛选）均有Figure 1b及S2支持；"k=5"与"DTW"在所提供摘录中无证据，距离度量证据仅为Bhattacharyya与Euclidian。
- **text-3｜有证据支持**：提出ORCtrL模型：以CNN-LSTM为骨干，接多个输出头形成prediction-and-selection结构，并通过optional rejection/coverage参数权衡精度、召回与覆盖。
  - 依据：method（S2）："an Optional-Reject Cnn-lstm deep learning model inspired by TRansfer-Learning (ORCtrL)"；Figure 2b：Optional-reject CNN-LSTM，CNN Block（Conv 1D→Avg pooling→Batch Norm）+ ×4 LSTM Block，右侧分出 Prediction 与 Selection 两个输出头，含 Recognized or not? True/False；Figure 4 referenced_text_spans："ORCtrL offers the flexibility to adjust the optional rejection module. This allows the coverage parameter to be tuned during training, with lower coverage typically resulting in hi..."
  - 证据 ID：S2、Figure 2、Figure 4
  - 说明：CNN-LSTM骨干、Prediction/Selection双输出头、coverage参数训练期可调均有直接证据；"权衡精度、召回与覆盖"为coverage机制的自然推论，与Figure 3f/g中access ratio表现一致。
- **text-4｜有证据支持**：面向纳米孔自适应采样随机访问：需在约420 bp/s速度下数百毫秒内完成分类与keep-or-reject决策，目标示例为F1-score > 0.95。
  - 依据：results（S4）："the ability to classify a DNA strand and make a keep-or-reject decision in hundreds of milliseconds (due to the sequencing speed of ~420 bp/s) with sufficient accuracy (e.g., F1-score > 0.95) to ensure data retrieval purity"
  - 证据 ID：S4
  - 说明：420 bp/s、数百毫秒、keep-or-reject、F1-score > 0.95示例阈值均与S4原文一致。
- **text-5｜有证据支持**：报告domain adaptation收益：120 min新域测序数据约200k reads，将性能由87%提升至超过94%。
  - 依据：experimental_setup（S3）："Domain adaptation using only 120 minutes of new sequencing data (~200k reads) boosts the model performance from 87% to over 94%"；Figure 3d：New sequencing+training 下 Weighted F1-score 由约0.87（10 min）升至约0.9410平台（120–180 min）
  - 证据 ID：S3、Figure 3
  - 说明：S3与Figure 3d互相印证：起始约87%，平台约0.9410（即94.10%，符合"over 94%"）。
- **text-6｜部分支持**：报告时间尺度随机访问结果：10 min、30 min、1 h、3 h测序下评估access purity、decoded ratio与富集；60 min数据按target N=14、non-target N=370统计。
  - 依据：Figure 4c：ORCtrl with domain adaptation 在 10/30/60/180 minutes 均为绿色对勾；Figure 4d：Access purity 随 Time (minutes) 变化（This work 接近1.0）；Figure 4e：Target decode ratio 随 Time (minutes) 变化（This work 接近1.0）；Figure 4f：60 Minutes 下 Avg./Total read counts，Target 与 Non-target 对比（富集/柱形比较）
  - 证据 ID：Figure 4
  - 说明：10/30/60/180 min四个时间点、access purity、target decode ratio与60 min富集（read counts）比较均有Figure 4直接支持；但"target N=14、non-target N=370"的具体样本量在摘录与图表中均未出现，无法核验。
- **text-7｜有证据支持**：图示比较显示SUSTag 96/384串扰低于ONT 96/Porcupine 96，但完整混淆矩阵数值未在摘录中给出。
  - 依据：Figure 3b：ONT 96 与 Porcupine 96 的 cross-talk ratio 分布更宽且位置偏高，SUSTag 96 与 SUSTag 384 分布更靠近低值且更窄；Figure 1e/f：Euclidian distances 2.02/2.88/4.02；Bhattacharyya distances 15.42/25.66/35.22（SUSTag 96 最大）；Figure 2c：三个混淆矩阵对角线为主，colorbar 仅清晰显示0与0.01，完整数值不可读
  - 证据 ID：Figure 3、Figure 1、Figure 2
  - 说明：SUSTag 96/384串扰更低的比较方向由Figure 3b（及Figure 1e/f的距离证据）支持；完整混淆矩阵数值确实未在摘录中给出，claim的限定陈述准确。注意图中无显著性标记，"更低"为分布趋势层面。
- **text-8｜缺少支持**：局限集中于R9.4.1迁移、软件流式延迟、模型量化/剪枝推理加速、PromethION扩展与复杂天然样本鲁棒性。
  - 依据：所提供的正文摘录（abstract/method/experimental_setup/results/conclusion，S1–S5）及图注摘录中均未包含Discussion/Limitations内容，无R9.4.1、流式延迟、量化/剪枝、PromethION或天然样本鲁棒性相关表述
  - 证据 ID：未明确说明
  - 说明：当前材料中不存在任何关于局限性的证据，所列具体局限点均无出处支持。
- **text-9｜部分支持**：作者、机构、完整数据可用性与部分实验参数在提供文本中未明确说明。
  - 依据：method（S2）末尾："e-mail: liy37@sustech.edu.cn"（提示通讯作者单位为南方科技大学SUSTech）；所提供摘录中无完整作者列表、单位全称及Data availability声明
  - 证据 ID：S2
  - 说明："部分实验参数/数据可用性未说明"成立，但"作者、机构未明确说明"不完全准确——S2中出现带sustech.edu.cn后缀的通讯邮箱，可推断机构信息存在；完整作者列表与数据可用性确实未在摘录中给出。
- **text-10｜有证据支持**：DNA存储随机访问需要在纳米孔测序过程中动态识别地址位并做keep-or-reject决策；现有PCR扩增或bead-based extraction依赖Watson-Crick base pairing与预定义引物，限制了测序中的动态决策。自适应采样还要求在约420 bp/s速度下数百毫秒内分类，并具有足够准确性，原文示例阈值为F1-score > 0.95。
  - 依据：method（S2）：PCR amplification or bead-based extraction rely on Watson-Crick base pairing and pre-defined primers, limiting dynamic decision-making whilst sequencing；results（S4）：classify a DNA strand and make a keep-or-reject decision in hundreds of milliseconds (due to the sequencing speed of ~420 bp/s) with sufficient accuracy (e.g., F1-score > 0.95)
  - 证据 ID：S2、S4
  - 说明：动态决策受限的问题陈述、420 bp/s、数百毫秒、F1-score > 0.95阈值均有原文直接证据。
- **text-11｜部分支持**：SUSTag：用scrappie v1.4.2模拟DNA序列电学签名，基于k=5 scrappie squiggle与实验μ/σ穷举4^8=65,536和4^9=262,144组合，DTW计算信号两两距离，可用Euclidean或Bhattacharyya distance，经距离混淆矩阵与incremental clustering完成de novo标签设计。ORCtrL：Optional-Reject CNN-LSTM deep learning model inspired by TRansfer-Learning，以CNN-LSTM backbone加多输出头构成prediction-and-selection，可训练时调节coverage参数；domain adaptation仅用120 min约200k reads新域数据。
  - 依据：Figure 4 referenced_text_spans："Methods SUSTag design algorithm We started from using the scrappie tool (v1.4.2) from Oxford Nanopore Technology (ONT) to simulate the electrical signatures from DNA sequences"；Figure 1b：8-mers (65,536) Best 400、9-mers (262,144) Best 400、17-mers: A+B B+A (320,000) Best 200、34-mers (40,000) Best 96/384；Bhattacharyya distance calculation、Distance matrix、Incremental clustering；method（S2）：ORCtrL为"Optional-Reject Cnn-lstm deep learning model inspired by TRansfer-Learning"；Figure 2b：CNN Block + ×4 LSTM Block，Prediction 与 Selection 双输出头；Figure 4 referenced_text_spans：coverage parameter to be tuned during training；experimental_setup（S3）：120 minutes of new sequencing data (~200k reads)
  - 证据 ID：S2、S3、Figure 1、Figure 2、Figure 4
  - 说明：scrappie v1.4.2、65,536/262,144组合穷举、Bhattacharyya/Euclidian距离、距离矩阵、增量聚类、ORCtrL命名与CNN-LSTM结构、双输出头、coverage可调、120 min/200k reads均有证据；但"k=5"、"实验μ/σ"与"DTW"在所提供摘录中无证据（scrappie工具与组合数已证实，具体k-mer长度参数未出现）。
- **text-12｜部分支持**：原文明确数值包括：domain adaptation用120 min新测序数据约200k reads，将模型性能由87%提升至超过94%，并在10 min到3 h实现complete recovery of target data with minimal crosstalk。图注称SUSTag 96与SUSTag 384的crosstalk显著低于ONT 96和Porcupine 96，error patterns相似；Fig.4给出三种方法随时间变化的access purity、target decoded ratio、富集与累计read yield，但摘录未提供具体解码率数值。
  - 依据：experimental_setup（S3）：120 minutes、~200k reads、87% to over 94%、complete recovery of target data with minimal crosstalk in 10 min to 3 h；Figure 3b：SUSTag 96/384 cross-talk ratio 分布低于 ONT 96/Porcupine 96（无显著性标记）；Figure 4d/e/f/g：Access purity、Target decode ratio、read counts、Yield 随时间/方法变化；具体数值点不可精确读取
  - 证据 ID：S3、Figure 3、Figure 4
  - 说明：domain adaptation数值、10 min–3 h恢复、Fig.4四类指标及"具体解码率数值未提供"均与材料一致；但"error patterns相似"在摘录与图注中无证据，且图中无显著性检验标记，"显著低于"的强度表述略超证据。
- **figure-13｜有证据支持**：作者声称结论（据图注与面板标签推断）：本文提出的 ORCtrl（This work）通过 384-multiplexed nanopore signatures 实现低串扰、动态决策的随机访问，在 PCR-free 随机访问中相比 Readfish 和 Porcupine 方法具有更高的 Access purity、Target decode ratio 和更快的成功解码时间，并能通过自适应采样在测序过程中实时富集目标读段。
  - 依据：Figure 4c：ORCtrl with domain adaptation 在10/30/60/180 minutes均为绿色对勾；Figure 4a Readfish在10/60 minutes为红色叉号；Figure 4b CNN (Porcupine)为黄色圆形符号；Figure 4d：Access purity——This work接近1.0，Readfish method约0.9后略降，Porcupine method降至约0.3；Figure 4e：Target decode ratio——This work接近1.0，Porcupine method约0.85–0.9，Readfish method约0.65→0.79；Figure 4f：60 Minutes下ORCtrl的Non-target柱明显更低、Target柱保留（富集）；Figure 4g：Random access (adaptive sampling) On/Off切换下Channel 1-256产率响应
  - 证据 ID：Figure 4
  - 说明：Figure 4各面板直接支持：ORCtrl在四个时间点均成功解码（更快成功解码时间），access purity与target decode ratio均高于Readfish和Porcupine，非目标读段被抑制（富集），panel g展示自适应采样实时切换。不确定性：panel a–c缩略图内文不可OCR、panel b黄色符号含义不明确、panel c黑色小方块含义不明、具体数值不可精确读取。
- **figure-14｜有证据支持**：作者声称结论（据图题推断）：SUSTag 设计流程能够生成特征距离更大的分子标签集合，SUSTag 96 相比 ONT 96 和 Porcupine 96 具有更大的欧氏距离与 Bhattacharyya 距离，即更低的地址间串扰，更适合作为 DNA 存储的寻址信息并支持 384 重多重签名。
  - 依据：Figure 1b：SUSTag design pipeline（Bhattacharyya distance、Distance matrix、Incremental clustering；8-mer/9-mer组合至34-mers Best 96/384）；Figure 1c/d：三个Euclidian与Bhattacharyya距离矩阵并列，SUSTag 96整体颜色较浅；Figure 1e：Euclidian distances——ONT 96: 2.02，Porcupine 96: 2.88，SUSTag 96: 4.02；Figure 1f：Bhattacharyya distances——ONT 96: 15.42，Porcupine 96: 25.66，SUSTag 96: 35.22
  - 证据 ID：Figure 1
  - 说明：SUSTag 96的Euclidian（4.02）与Bhattacharyya（35.22）距离均明确大于ONT 96与Porcupine 96，设计流程支持96/384重输出，结论与图示证据一致。"即更低串扰"为距离-串扰关系的解释，与Figure 3b的cross-talk分布一致。
- **figure-15｜有证据支持**：作者声称结论（据图题与面板标注推断）：域适应可将基于质粒序列训练的分类器迁移到合成序列 DNA 存储应用，优化的域适应显著提高 Weighted F1-score（可达约 0.9456）并降低非目标访问（串扰），且增加适应数据量比单纯延长测序时间更高效；SUSTag 设计本身具有更低的 cross-talk ratio。
  - 依据：Figure 3a：Plasmid Sequences 经箭头指向 Synthetic Sequences 的domain adaptation，地址片段布局含34 nt SUSTag 384；Figure 3c：Weighted F1-score 随Adapted data amount由约0.92升至约0.9456平台；Figure 3d：New sequencing+training由约0.87（10 min）升至约0.9410平台；Figure 3e：Increasing data amount (equalized) 轨迹整体高于 Increasing sequencing time (inequalized)；Figure 3f/g：域适应后Non-target黄色柱明显减少、接近0；Figure 3b：SUSTag 96/384 cross-talk ratio分布更低更窄
  - 证据 ID：Figure 3
  - 说明：0.9456平台值、F1随数据量与测序时间上升、equalized轨迹优于inequalized、域适应降低非目标访问、SUSTag低cross-talk均有面板直接证据。注意图中无显著性标记，"显著"应理解为趋势层面；"基于质粒序列训练"由Plasmid→Synthetic迁移示意支持。
- **figure-16｜有证据支持**：作者声称结论（据图题与面板标注推断）：SUSTag 96 是三种标签设计中分类性能最好的（F1-score 0.9969），且本文提出的 CNN-LSTM（ORCtrl 分类器核心）优于普通 CNN 与 Porcupine 的 CNN 方法，在 weighted precision–recall 上整体处于更高水平，验证了低串扰标签与可选拒绝分类器结合的有效性。
  - 依据：Figure 2c：F1-score——ONT 96: 0.9925，Porcupine 96: 0.9891，SUSTag 96: 0.9969；Figure 2d：F1-score——CNN (Porcupine): 0.9543，CNN: 0.9852，CNN-LSTM: 0.9892；Figure 2e：Weighted recall–precision散点中CNN-LSTM位于右上、CNN居中、ORCtrl位于左下；Figure 2b：Optional-reject CNN-LSTM结构（CNN Block + ×4 LSTM Block + Prediction/Selection双输出头）
  - 证据 ID：Figure 2
  - 说明：SUSTag 96的0.9969为三者最高，CNN-LSTM的0.9892高于CNN（0.9852）与CNN (Porcupine)（0.9543），散点位置支持precision-recall整体更高水平。小不确定项：panel b右侧1–96网格与barcode示例字号过小无法逐一OCR；panel d是否全部对应同一tag设计依赖图注语境。
- **规则预检查提示**：
  - text-1：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-2：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-3：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-4：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-5：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-6：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-6：数值 370 未在原文或图表证据中出现。
  - text-7：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-8：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-9：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-10：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-11：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - text-12：未引用 evidence ID 或来源章节，核验时需额外谨慎。
  - figure-13：证据片段未在原文中找到（可能被改写或虚构）：panel a（Readfish 条件）：10 minutes 与 60 min
  - figure-13：证据片段未在原文中找到（可能被改写或虚构）：panel b（CNN (Porcupine) 条件）：10 minutes 与
  - figure-13：证据片段未在原文中找到（可能被改写或虚构）：panel c（ORCtrl with domain adaptation 条件
  - figure-14：证据片段未在原文中找到（可能被改写或虚构）：panel a：展示数字内容（Texts, images, …）经 DNA 合成
  - figure-14：证据片段未在原文中找到（可能被改写或虚构）：panel b：展示 SUSTag design pipeline，包括两条标为
  - figure-14：证据片段未在原文中找到（可能被改写或虚构）：panel c：并列显示 ONT 96、Porcupine 96、SUSTag
  - figure-15：证据片段未在原文中找到（可能被改写或虚构）：panel a：示意从 Plasmid Sequences 经箭头指向 Synt
  - figure-15：证据片段未在原文中找到（可能被改写或虚构）：panel b：ONT 96 与 Porcupine 96 的 cross-ta
  - figure-15：证据片段未在原文中找到（可能被改写或虚构）：panel c：Weighted F1-score 随 Adapted data
  - figure-16：证据片段未在原文中找到（可能被改写或虚构）：panel a：线性序列结构从左到右为 Primer (23 nt)、8×T (
  - figure-16：证据片段未在原文中找到（可能被改写或虚构）：panel b：Optional-reject CNN-LSTM 结构包含 CN
  - figure-16：证据片段未在原文中找到（可能被改写或虚构）：panel c：ONT 96、Porcupine 96、SUSTag 96 三个

## 8. 评价
### 8.1 优点
- 标签设计直接优化信号可分性而非仅碱基序列
- 串扰指标与混淆矩阵设计较系统
- optional rejection提供precision/coverage可调性
- 少量新域数据即可提升跨域适应性
- 同时给出in silico与实验 benchmarking

### 8.2 局限性
- 摘录不完整，部分关键数值未给出
- 当前主要适配R9.4.1，R10迁移待完成
- 实时流式分类延迟仍需工程优化
- 复杂天然样本背景下的稳健性未验证
- 作者、数据可用性与完整实验流程未明确说明

### 8.3 可复现性
{'status': '部分可复现；提供文本不完整', 'explicit_details': ['scrappie v1.4.2', 'k=5 scrappie squiggle', '4^8=65,536与4^9=262,144穷举组合', 'DTW pairwise distances', 'Euclidean distance或Bhattacharyya distance', 'ONT 96、Porcupine 96、SUSTag 96/384', '质粒pCDB180', 'ORCtrL target coverage 0.95', 'domain adaptation 120 min约200k reads', 'Fig.4 target N=14、non-target N=370', '讨论中提及R9.4.1 flow cells'], 'missing_or_unclear': ['作者列表', '完整测序平台与flow cell批次', '原始数据/代码可用性声明', '完整引物与载体构建细节', '具体access purity/decoded ratio数值', 'ORCtrL超参数与训练配置', 'Supplementary Table S2内容']}

## 9. 启发与参考价值
### 9.1 适用场景
该方法可优先参考于与 未明确说明完整公开数据集。文中涉及标签集合：ONT 96、Porcupine 96、SUSTag 96、SUSTag 384；序列结构含SUSTag/ONT 96/Porcupine 96、引物及质粒pCDB180任意片段；随机访问统计中target组为barcodes #29到#42，N=14，non-target组N=370；domain adaptation使用约200k reads；对比方法包括Readfish与Porcupine；先验DeePlexiCon为Novoa group在DRS四组20 bp barcode结果，非本文新结果。 类似的数据或任务场景。

### 9.2 对当前研究的启发
SUSTag：将纳米孔电学签名作为寻址信息并进行低串扰de novo设计 联合Bhattacharyya distance、distance confusion matrix与incremental clustering的标签生成策略 ORCtrL：CNN-LSTM骨干加optional-reject多输出头，训练期可调coverage 用少量新域数据做transfer-learning/domain adaptation以适应信号变异 面向384 address bits的自适应纳米孔随机访问演示

## 10. 总结
本文针对DNA存储中靶向检索依赖PCR扩增或bead-based extraction、受Watson-Crick base pairing与预定义引物限制、难以在测序过程中做动态keep-or-reject决策的问题，提出SUSTag分子标签设计与ORCtrL可选拒绝CNN-LSTM深度学习模型相结合的框架。SUSTag利用scrappie squiggle信号、DTW距离与增量聚类降低标签间串扰；ORCtrL通过CNN-LSTM骨干、多输出头与可调的optional rejection/coverage参数适应纳米孔信号变异。原文报告仅用120分钟新测序数据约200k reads做domain adaptation可将模型表现由87%提升至超过94%，并在10 min到3 h实现目标数据完全恢复且串扰较低；图注还称SUSTag 96/384的crosstalk显著低于ONT 96与Porcupine 96。需要注意，提供文本为不完整摘录，作者列表、完整协议与部分数值解码率未明确说明，R10迁移、PromethION扩展与复杂天然样本仍属工程化/未来方向。
