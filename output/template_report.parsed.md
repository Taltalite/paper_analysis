# PDF 结构化解析

## 基础信息
- **标题：** Scalable and robust DNA-based storage via coding theory and deep learning
- **作者：** Daniella Bar-Lev, Itai Orr, Omer Sabary, Tuvi Etzion, Eitan Yaakobi
- **DOI：** 10.1038/s42256-025-01003-z
- **期刊/会议：** Nature Machine Intelligence | Volume 7 | April 2025 | 639–649 639
- **年份：** 2025
- **页数：** 2
- **图表数量：** 1

## 图表元数据

### Figure 1
- **Caption：** Fig. 1 | End-to-end solution for DNA information retrieval. a, A schematic description of our solution for the DNA-based storage pipeline. The different stages through the process are labelled 1–6 and steps that are part of the training
- **页码：** 2
- **页截图路径：** input/.paper_analysis_assets/template/page_2.png
- **正文引用：**
- The reconstruction algorithm is applied on each cluster of reads
- pipeline are labelled iv–vi. b, A detailed view of the information retrieval process showing the DNN architecture, confidence filer, CPL and the input to the decoder. Figure created with BioRender.com.

## 摘要（Abstract）
The global data sphere is expanding exponentially, projected to hit 180 zettabytes by 2025, whereas current technologies are not anticipated to scale at nearly the same rate. DNA-based storage emerges as a crucial solution to this gap, enabling digital information to be archived in DNA molecules. This method enjoys major advantages over magnetic and optical storage solutions such as exceptional information density, enhanced data durability and negligible power consumption to maintain data integrity. To access the data, an information retrieval process is employed, where some of the main bottlenecks are the scalability and accuracy, which have a natural tradeoff between the two. Here we show a modular and holistic approach that combines deep neural networks trained on simulated data, tensor product-based error-correcting codes and a safety margin mechanism into a single coherent pipeline. We demonstrated our solution on 3.1 MB of information using two different sequencing technologies. Our work improves upon the current leading solutions with a 3,200× increase in speed and a 40% improvement in accuracy and offers a code rate of 1.6 bits per base in a high-noise regime. In a broader sense, our work shows a viable path to commercial DNA storage solutions hindered by current information retrieval processes.

## 引言（Introduction）
There is unsustainable growth in the global data sphere, fuelled by the proliferation of digital technologies such as artificial intelligence, the Internet of Things, widespread internet connectivity and the growing number of interconnected devices. While the global data sphere is anticipated to reach 180 zettabytes by 2025, current storage solutions are not expected to scale at nearly the same pace owing to capacity limitations1. To address this urgent need of the digital age, researchers are turning to innovative solutions such as DNA-based storage, recognizing its potential to revolutionize long-term data storage capabilities by offering extraordinary data density and durability2,3. A DNA molecule consists of four building blocks called nucleotides: adenine (A), cytosine (C), guanine (G) and thymine (T). A DNA strand, or oligonucleotide, is an ordered sequence of nucleotides, represented as a string over the alphabet {A,C,G,T}. The ability to chemically synthesize almost any possible strand makes it possible to store digital data on DNA molecules. The standard in vitro DNA-based storage pipeline consists of several steps and is shown in Fig. 1a. First, the binary data are encoded into sequences over the DNA 4-ary alphabet, which are referred to as encoded sequences. Next, the encoded sequences are synthesized by a DNA synthesizer. Since current synthesis technologies cannot produce one single strand per sequence, multiple DNA strands (known as oligos) are produced per encoded sequence. Moreover, the length of the strands produced by the synthesizer is typically bounded by roughly 200–300 nucleotides to sustain an acceptable error rate4. The synthesized strands are then stored in a storage container in an unordered manner. To access the data, a sample of the strands is taken from the storage container, amplified using PCR and then sequenced by a DNA sequencer. The sequencer processes the strands and generates

## 方法（Method）
This method enjoys major advantages over magnetic and optical storage solutions such as exceptional information density, enhanced data durability and negligible power consumption to maintain data integrity. Here we show a modular and holistic approach that combines deep neural networks trained on simulated data, tensor product-based error-correcting codes and a safety margin mechanism into a single coherent pipeline. The standard in vitro DNA-based storage pipeline consists of sev- eral steps and is shown in Fig. a, A schematic description of our solution for the DNA-based storage pipeline.

## 实验设置（Experimental Setup）
We demonstrated our solution on 3.1 MB of information using two different sequencing technologies. The standard in vitro DNA-based storage pipeline consists of sev- eral steps and is shown in Fig. The sequencer processes the strands and generates

Nature Machine Intelligence | Volume 7 | April 2025 | 639–649 640

001010 110100 010011 111011 110010

1 Encoding of the binary information using an ECC and a constraint code

2 Synthetic DNA strands are synthesized using a DNA synthesis technology

Multipel copies for each DNA strand

3 Sequencing an amplified sample from the DNA storage container using a DNA sequencer

The number of reads for each encoded sequence can vary, and some encoded sequences may have zero or a very small number of reads Reads of the encoded sequences

4 Binning the reads into clusters

Incorrect assignment of reads into clusters

6 Decoding of the reconstructed data to correct the remaining errors and retrieve the binary

NCI aligner Embedding module Transformer module

Shared weights Shared weights Shared weights

IV Analysed noise statistics V Generating simulated data for training VI DNN training

The reconstruction algorithm is applied on each cluster of reads

Fig. a, A schematic description of our solution for the DNA-based storage pipeline.

## 结果（Results）
To access the data, an information retrieval process is employed, where some of the main bottlenecks are the scalability and accuracy, which have a natural tradeoff between the two. Our work improves upon the current leading solutions with a 3,200× increase in speed and a 40% improvement in accuracy and offers a code rate of 1.6 bits per base in a high-noise regime.

## 结论（Conclusion）
In a broader sense, our work shows a viable path to commercial DNA storage solutions hindered by current information retrieval processes.
