# PDF 结构化解析

## 基础信息
- **标题：** Empowering low-crosstalk, dynamicdecision random access of DNA storage via 384-multiplexed nanopore signatures
- **作者：** Junyao Li, Xuyang Zhao, Qingyuan Fan, Yanping Long, Ronghui Liu, Jixian Zhai, Qing Pan, Yi Li On-demand, Optional-Reject Cnn-lstm, SUSTagORCtrL, Multiplexed DNA, These DNA
- **DOI：** 10.1038/s41467-025-64293-2
- **期刊/会议：** cell heterogeneity and gene regulatory linkages4. Furthermore, quantitatively detecting blood biomarkers to advance clinical diagnostics beyond the single biomarker model has been demonstrated using DNA-barcoded probes5. Beyond these applications, DNA tags emerge as a growing alternative to conventional electronic sensing and computing methods. For instance, Koch et al. have assessed the ecotoxicity
- **年份：** 2025
- **页数：** 12
- **图表数量：** 4

## 证据索引
- **S1**：摘要（Abstract）
- **S2**：方法（Method）
- **S3**：实验设置（Experimental Setup）
- **S4**：结果（Results）
- **S5**：结论（Conclusion）
- **Figure 1**：图表证据 ID
- **Figure 2**：图表证据 ID
- **Figure 3**：图表证据 ID
- **Figure 4**：图表证据 ID

## 图表元数据

### Figure 1
- **Caption：** Fig. 1 | Design of low-crosstalk molecular tags featured with nanopore signatures as addressing information for DNA storage. a Schematics of random access using nanopore sequencing for digital contents stored in DNA. Orange current fluctuations represent signatures for specific addressing bits. b De novo design method for proposed SUSTag including maximized Bhattacharyya distance, distance confusion matrix and incremental clustering. c In silico performance evaluation for ONT 96, Porcupine 96 and SUSTag 96 using Euclidean distance matrices. d In silico performance evaluation for ONT 96, Porcupine 96 and SUSTag 96 using Bhattacharyya distance matrices. Statistical comparison of in silico Euclidean (e) and Bhattacharyya (f) distances. For each 96-plex set, the data distribution is shown as a violin plot, derived from N = 200 randomly sampled pairs of distinct barcodes. The inner box plot indicates the median (center line), interquartile range (IQR, box bounds), and whiskers (1.5×IQR). The separate bar chart and value highlight the observed minimal distance. Article https://doi.org/10.1038/s41467-025-64293-2
- **页码：** 3
- **页截图路径：** ref_baseline/.paper_analysis_assets/s41467-025-64293-2/pages/page_3.png
- **正文引用：**
- 未明确说明

### Figure 2
- **Caption：** Fig. 2 | Experimental benchmarking of tag designs and deep-learning classifiers. a Sequence structure containing SUSTag and other tags (ONT 96 and Porcupine 96) as well as primer sequences and an arbitrary portion of plasmid pCDB180. b Schematic diagram of the optional-reject CNN-LSTM network architecture. The model uses a CNN-LSTM network as the backbone, followed by multiple output heads forming a predictionand selection structure. c Experimental confusion matrices for classifying different barcode designs (ONT, Porcupine and SUSTag 96) using the ORCtrL model. The ORCtrL model was trained with a target coverage of 0.95. d Experimental confusion matrices for classifying SUSTag 96 using three deep-learning methods: they are CNN (Porcupine), CNN and CNNLSTM. e Precision vs. Recall for classifying three types of barcode designs using three different deep-learning models. The ORCtrL model was trained with a target coverage of 0.95. Orange, Navy Blue and Purple stand for SUSTag, ONT and Porcupine designs. Source data are provided as a Source Data file. Article https://doi.org/10.1038/s41467-025-64293-2
- **页码：** 5
- **页截图路径：** ref_baseline/.paper_analysis_assets/s41467-025-64293-2/pages/page_5.png
- **正文引用：**
- 未明确说明

### Figure 3
- **Caption：** Fig. 3 | Domain adaptation for DNA storage application. a Illustration of address bits (barcodes) for DNA information storage. b Statistical chart of error patterns for four barcode classifications. The crosstalk of SUSTag 96 and SUSTag 384 is significantly lower than that of ONT 96 and Porcupine 96, with similar error patterns observed. c Weighted F1-score as a function of data amount from new domain. d Weighted F1-score as a function of total running time (sequencing plus training) for new domain data. e Scatter plot of both equalized data volume evolved (orange) and equalized sequencing time evolved (cyan) effect of different fine-tuning datasets on model performance. The gray points show the performance of the model without domain adaptation as a control. f Access ratios of 384 address bits for the ORCtrL model without domain adaptation. g Access ratios of the identical 384 address bits after domain adaptation. Source data are provided as a Source Data file. Source data are provided as a Source Data file. Article https://doi.org/10.1038/s41467-025-64293-2
- **页码：** 6
- **页截图路径：** ref_baseline/.paper_analysis_assets/s41467-025-64293-2/pages/page_6.png
- **正文引用：**
- 未明确说明

### Figure 4
- **Caption：** Fig. 4 | Adaptive nanopore sequencing based random access in DNA storage. a Decoding results of PCR-free random-access data obtained using the Readfish method with 10 min and 1 h of sequencing data. b Decoding results of PCR-free random-access data obtained using the Porcupine method with 10 min and 1 h of sequencing data. c Decoding results of random-accessed data obtained using the proposed method with 10 min, 30 min, 1 h, and 3 h of sequencing data. d Access purity changes over time for the three methods. e Target sequences decoded ratio changes over time for the three methods. f Sequencing data enrichment performance of the three methods, derived from a 60-minute sequencing data. In the left panel, bars represent the mean read counts per barcode, with error bars indicating the standard deviation (SD). The right panel shows the total number of reads classified for each method. The statistics were calculated across distinct barcode categories within each group. N = 14 for the target group (barcodes #29 to #42) and N = 370 for the non-target group. g Comparison of cumulative read yields over time between adaptive sampling channels and control channels. Source data are provided as a Source Data file. Article https://doi.org/10.1038/s41467-025-64293-2
- **页码：** 8
- **页截图路径：** ref_baseline/.paper_analysis_assets/s41467-025-64293-2/pages/page_8.png
- **正文引用：**
- needed for other DNA storage systems, ORCtrL offers the flexibility to adjust the optional rejection module. This allows the coverage para- meter to be tuned during training, with lower coverage typically resulting in higher precision and, consequently, reduced crosstalk (Supplementary Table S2). While deep learning architectures are constantly evolving, we anticipate that the optional rejection module will remain a core component. Future enhancements could involve incorporating more sophisticated networks to further improve accu- racy or streamlining the network for faster processing speeds, depending on the specific computational resources and performance demands. Notably, the SUSTag design methodology currently does not impose any limits on the arbitrary number of tags or pore model, resulting for the nonlinear projection from ionic current signals to base sequences. The scalability of SUSTag is facilitated by our dynamic incremental clustering strategy, which allows for customization of the final design based on individual requirements. As tools for simulating sequencing signals from R10 pore model mature, our design method can be seamlessly migrated from R9.4.1 flow cells. For instance, seq2squiggle43 has recently demonstrated remarkable similarity to real data on the R10.4.1 flow cell, providing a powerful tool for simulating nanopore sequencing signals with the latest generation of flow cells. We plan to extend the SUSTag to the R10 flow cell to accommodate the unique current signal characteristics of newer nanopore chemistries and explore the full potential of this molecular tagging system. While we have now demonstrated the feasibility of random access, engi- neering developments are still required for widespread adoption. These include further minimizing the software latency between data streaming and classification, optimizing the model architecture (e.g., through quantization or pruning) for faster inference, and scaling the real-time pipeline to handle the data deluge from high-throughput sequencers like PromethION. Furthermore, the ultimate test will be applying this system to complex native biological samples, where performance must be maintained against a noisy and variable back- ground. Overcoming these challenges will be key to unlocking the full potential of dynamic nanopore sequencing for the wide range of applications.
- Methods SUSTag design algorithm We started from using the scrappie tool (v1.4.2) from Oxford Nanopore Technology (ONT) to simulate the electrical signatures from DNA sequences, which aims to produce the differences on electrical signals as large as possible. These DNA sequences (also termed as barcodes or tags) are designed as the following three steps: First, simulated current signals of 48 = 65,536 and 49 = 262,144 combinations were exhaustively generated based on the known k-mer table with experimental mean current μ and standard deviation σ for k-mers (k = 5, scrappie squiggle). Sec- ond, Dynamic Time Warping (DTW) algorithm was applied to calculate pairwise distances between the squiggled signals, resulting in a distance matrix. The pairwise distance can be cal- culated by either Euclidean distance or Bhattacharyya distance. The formula for calculating the Euclidean distance DE and Bhattacharyya distance DB between signal p N ðμp, σ2 pÞ and

## 摘要（Abstract）
of surface and underground tracing of natural waterflows using encapsulated DNA tags6. Recognized as fingerprints for the hybridization process, DNA barcodes were proposed7 and demonstrated8 for encrypted, content-based DNA similarity search. DNA tags can also act as programmable elements, directing reactions and implementing logic functions9 and DNA-based programmable gate arrays10. Thus, accurate and on-demand manipulation of DNA tags is the highway to success in DNA-of-things11, content-based similarity search8, information processing12 as well as data storage13. Targeted DNA capture, also known as target enrichment, has become the key for realizing the full potential of DNA tags14. In the era

## 方法（Method）
However, contemporary methods for targeted retrie- val using PCR amplification or bead-based extraction, rely on Watson-Crick base pairing and pre-defined primers, limiting dynamic decision-making whilst sequencing. Our fra- mework combines SUSTag, a Bhattacharyya distance and incremental clus- tering enhanced molecular tag design (SUSTag) to minimize crosstalk, with an Optional-Reject Cnn-lstm deep learning model inspired by TRansfer-Learning (ORCtrL), designed to enhance adaptability to signal variability. Beyond these applications, DNA tags emerge as a growing alternative to conventional electronic sensing and com- puting methods. e-mail: liy37@sustech.edu.cn

Nature Communications| (2025) 16:9233 1

1234567890():,;

1234567890():,;

of next-generation sequencing (NGS), researchers typically employed targeted PCR amplification with specific primers or hybridization- based methods to selectively sequence desired regions15–17.

## 实验设置（Experimental Setup）
However, contemporary methods for targeted retrie- val using PCR amplification or bead-based extraction, rely on Watson-Crick base pairing and pre-defined primers, limiting dynamic decision-making whilst sequencing. Domain adaptation using only120 minutes of new sequencing data ( ~ 200k reads) boosts the model performance from 87% to over 94%, achieving complete recovery of target data with minimal crosstalk in 10 min to 3 h. Furthermore, quantita- tively detecting blood biomarkers to advance clinical diagnostics beyond the single biomarker model has been demonstrated using DNA-barcoded probes5. Recognized as fingerprints for the hybridi- zation process, DNA barcodes were proposed7 and demonstrated8 for encrypted, content-based DNA similarity search.

## 结果（Results）
With ongoing advancements in stability and accuracy of nanopore sequencing23, adaptive sampling is gaining growing interest in its potential for ran- dom access to the information stored in DNA24. Achieving these goals requires exceptional performance, including the ability to classify a DNA strand and make a keep-or-reject decision in hundreds of milli- seconds (due to the sequencing speed of ~420 bp/s) with sufficient accuracy (e.g., F1-score > 0.95) to ensure data retrieval purity. On one hand, deep-learning methods were applied onto commercially available barcodes from ONT with increasing accuracy and/or recall rates. Novoa group showed that DeePlexiCon demultiplexed four 20 bp barcodes for direct RNA nanopore sequencing (DRS) with up to 99.4% accuracy and 98.9% recall33.

## 结论（Conclusion）
On one hand, deep-learning methods were applied onto commercially available barcodes from ONT with increasing accuracy and/or recall rates. Open Access This article is licensed under a Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License, which permits any non-commercial use, sharing, distribution and reproduction in any medium or format, as long as you give appropriate credit to the original author(s) and the source, provide a link to the Creative Commons licence, and indicate if you modified the licensed material.
