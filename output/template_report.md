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
Fig. 1 | End-to-end solution for DNA information retrieval. a, A schematic description of our solution for the DNA-based storage pipeline. The different stages through the process are labelled 1–6 and steps that are part of the training

## 研究问题
解决DNA存储中可扩展性与准确性之间的权衡，通过端到端信息检索管线提升读取速度与准确性。

## 核心方法
将深度神经网络（在模拟数据上训练）、张量积纠错编码、以及安全余量机制整合到一个统一管线；涉及的DNA存储流程包括：将二进制数据编码为DNA 4碱基符号、合成、存储、PCR扩增、测序、读数分箱、解码纠错并检索原始二进制数据。

## 数据集
未公开指明具体数据集名称或来源；实验在3.1 MB信息量上进行演示。

## 实验设置
演示规模为3.1 MB信息量，使用两种测序技术；流程包括ECC与约束编码、合成、同一序列的多拷贝、测序、读数分箱、解码等阶段；涉及组件如NCI aligner、Embedding模块、Transformer模块，及训练数据生成与DNN训练。

## 主要结果
相较于当前领先方案，速度提升约3200×，准确性提升约40%，在高噪声条件下码率达到1.6比特/碱基；提出方法被视为商业DNA存储解决方案的可行路径。

## 创新点
端到端信息检索管线的整合，结合深度学习、张量积纠错编码与安全余量机制 在实际DNA存储管道中实现对读取误差的显著鲁棒性提升与更高吞吐 在高噪声场景下保持较高码率的能力

## 优点
- 显著的速度提升与准确性提高
- 提供了一个整体框架，将多个技术组件协同工作以解决信息检索瓶颈
- 在实际测序条件下给出可观的码率与鲁棒性结果

## 局限性
- 缺乏公开数据集和可重复性细节
- 规模与场景受限，需验证大规模部署的鲁棒性
- 成本与商业化可行性分析不足

## 复现建议
论文未提供详细的数据集信息与实现细节，复现实验需额外获取测试数据与配置参数

## 总结
本研究提出一个端到端的信息检索管线，用以提升DNA存储的速度与准确性。通过在模拟数据上训练的深度神经网络、基于张量积的纠错编码，以及一个安全余量机制，将这些组件整合为一个统一流程，在3.1 MB数据量和两种测序技术的条件下演示。相比当前领先方案，实现了约3200倍的速度提升、约40%的准确性提升，并在高噪声环境下达到1.6比特/碱基的码率，指示该方法具备向商业化DNA存储解决方案演进的潜力，缓解现有信息检索环节的瓶颈。
