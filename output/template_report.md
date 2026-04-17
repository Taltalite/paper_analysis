# 研究型文献分析报告

## 来源文档
- **标题：** Scalable and robust DNA-based storage via coding theory and deep learning
- **作者：** Daniella Bar-Lev, Itai Orr, Omer Sabary, Tuvi Etzion, Eitan Yaakobi
- **DOI：** 10.1038/s42256-025-01003-z
- **期刊/会议：** Nature Machine Intelligence | Volume 7 | April 2025 | 639–649 639
- **年份：** 2025
- **页数：** 2

## 参与分析的重点章节
- 摘要（Abstract）
- 引言（Introduction）
- 方法（Method）
- 实验设置（Experimental Setup）
- 结果（Results）
- 结论（Conclusion）
- 图示（Figures）

## 结构化解析预览
### 摘要（Abstract）
The global data sphere is expanding exponentially, projected to hit 180 zettabytes by 2025, whereas current technologies are not anticipated to scale at nearly the same rate. DNA-based storage emerges as a crucial solution to this gap, enabling digital information to be archived in DNA molecules. This method enjoys major advantages over magnetic and optical storage solutions such as exceptional information density, enhanced data durability and negligible power consumption to maintain data integrity. To access the data, an information retrieval process is employed, where some of the main bottlenecks are the scalability and accuracy, which have a natural tradeoff between the two. Here we show

### 引言（Introduction）
There is unsustainable growth in the global data sphere, fuelled by the proliferation of digital technologies such as artificial intelligence, the Internet of Things, widespread internet connectivity and the growing number of interconnected devices. While the global data sphere is anticipated to reach 180 zettabytes by 2025, current storage solutions are not expected to scale at nearly the same pace owing to capacity limitations1. To address this urgent need of the digital age, researchers are turning to innovative solutions such as DNA-based storage, recognizing its potential to revolutionize long-term data storage capabilities by offering extraordinary data density and durability2,3. A DNA

### 方法（Method）
This method enjoys major advantages over magnetic and optical storage solutions such as exceptional information density, enhanced data durability and negligible power consumption to maintain data integrity. Here we show a modular and holistic approach that combines deep neural networks trained on simulated data, tensor product-based error-correcting codes and a safety margin mechanism into a single coherent pipeline. The standard in vitro DNA-based storage pipeline consists of sev- eral steps and is shown in Fig. a, A schematic description of our solution for the DNA-based storage pipeline.

### 实验设置（Experimental Setup）
We demonstrated our solution on 3.1 MB of information using two different sequencing technologies. The standard in vitro DNA-based storage pipeline consists of sev- eral steps and is shown in Fig. The sequencer processes the strands and generates

Nature Machine Intelligence | Volume 7 | April 2025 | 639–649 640

001010 110100 010011 111011 110010

1 Encoding of the binary information using an ECC and a constraint code

2 Synthetic DNA strands are synthesized using a DNA synthesis technology

Multipel copies for each DNA strand

3 Sequencing an amplified sample from the DNA storage container using a DNA sequencer

The number of reads for each encoded sequence can vary, and some encoded seque

### 结果（Results）
To access the data, an information retrieval process is employed, where some of the main bottlenecks are the scalability and accuracy, which have a natural tradeoff between the two. Our work improves upon the current leading solutions with a 3,200× increase in speed and a 40% improvement in accuracy and offers a code rate of 1.6 bits per base in a high-noise regime.

### 结论（Conclusion）
In a broader sense, our work shows a viable path to commercial DNA storage solutions hindered by current information retrieval processes.

### 图示（Figures）
### Figure 1
Fig. 1 | End-to-end solution for DNA information retrieval. a, A schematic description of our solution for the DNA-based storage pipeline. The different stages through the process are labelled 1–6 and steps that are part of the training

正文引用：
- The reconstruction algorithm is applied on each cluster of reads
- pipeline are labelled iv–vi. b, A detailed view of the information retrieval process showing the DNN architecture, confidence filer, CPL and the input to the decoder. Figure created with BioRender.com.

## 研究问题
未明确说明

## 核心方法
未明确说明

## 数据集
未明确说明

## 实验设置
未明确说明

## 主要结果
未明确说明

## 创新点
未明确说明

## 优点
- 未明确说明

## 局限性
- 未明确说明

## 复现建议
未明确说明

## 图像实验结果分析
### Figure 1
- **图注：** Fig. 1 | End-to-end solution for DNA information retrieval. a, A schematic description of our solution for the DNA-based storage pipeline. The different stages through the process are labelled 1–6 and steps that are part of the training pipeline are labelled iv–vi. b, A detailed view of the information retrieval process showing the DNN architecture, confidence filer, CPL and the input to the decoder. Figure created with BioRender.com.
- **实验焦点：** 端到端的DNA信息检索解决方案及信息检索过程的DNN架构与解码输入
- **比较对象：** 未明确说明
- **指标 / 坐标：** 1–6 标注的存储管道阶段, iv–vi 标注的训练流程步骤, DNN 架构、置信度筛选器、CPL、解码器输入
- **主要观察：**
- 图1a给出一个DNA信息存储管道的端到端示意，流程分为若干阶段并标注为1–6，训练流程标注为iv–vi。
- 图1b给出信息检索过程的详细视图，显示了DNN架构、置信度筛选器、CPL以及解码器输入。
- **作者结论：** 通过端到端的解决方案和DNN信息检索架构，实现DNA信息的存储、检索及解码流程的协同工作，提升信息检索过程的准确性与鲁棒性（通过训练阶段的标注及DNN组件的组合）。
- **置信度：** 不足以判断

## 关键图表结论
- Figure 1：通过端到端的解决方案和DNN信息检索架构，实现DNA信息的存储、检索及解码流程的协同工作，提升信息检索过程的准确性与鲁棒性（通过训练阶段的标注及DNN组件的组合）。

## 图文一致性检查
- Figure 1： caption 与正文引用的描述一致，图1a/1b的内容与文本中对端到端流程及DNN架构的描述一致；图像质量未知，未提供具体的性能指标或定量结果，仅是结构性示意。（置信度：不足以判断）

## 总结
未明确说明
