# 分块提升转置：相关工作与实现核对

检索日期：2026-11-17。用途：为本项目的单项工程实验划定边界，不是完成一份全面综述，也不宣称新的研究贡献。只读相关系统，不安装或测量外部对比框架。

## 判断

**可以把输出行分块作为小规模工程实验，但不能把“查表、分级累加、融合转置、缓存分块”本身作为新颖性主张。** Vec-LUT 已提出融合输出转换和分级累加；T-MAC 已做循环重排、tiling、低精度聚合；矩阵转置的局部性优化也已有长期研究。本项目要验证的窄问题是：在安全累加段 K=128 的具体实现中，改变 INT16→INT32 提升的遍历顺序，能否降低整个正确算子的耗时。

## 实际阅读范围

| 来源与版本 | 本轮核对位置/状态 | 对本实验的约束 |
|---|---|---|
| [Vec-LUT v2](https://arxiv.org/html/2512.06443v2)，MobiSys 2026 | 复核 §3.3 输出转换、§3.4 分级累加、§4 实现；结合本地完整源码 | 已有转换融合；本实验只是融合循环内部的访问顺序改进。不能声称首次消除独立转置。 |
| [T-MAC v2](https://arxiv.org/html/2407.00088v2)，EuroSys 2025 | 定向核对 §3.2–3.3、§4 聚合和 swizzling，以及 qgemm.py 的 compute/schedule | 布局、分块、聚合都已有先例。其快速 8-bit averaging 存在精度权衡，本项目不引入这种数值变化。 |
| [Bitnet.cpp v1](https://arxiv.org/html/2502.11880v1) | 本轮确认摘要、方法分区与作者 artifact；完整 §3/附录需进一步复核 | 三值打包与 LUT 是已有基础；不能将修复累加溢出作为新算法。 |
| [1-bit AI Infra Part 1.1 v2](https://arxiv.org/html/2410.16144v2) | 定向核对 §2 的 I2_S/TL1/TL2，§3 的设备/线程口径 | 不混淆解包乘加、三值查表与本项目 I1/I2 格式；其设备速度不可外推本机。 |
| [Pushing the Envelope of LLM Inference on AI-PC v1](https://arxiv.org/html/2508.06753v1) | 定向核对 §III-A/B 微内核与交织权重布局 | 数据布局必须适配执行指令；该工作走解包与 int8 点积，本项目只动累加输出，不替换计算范式。 |
| [LUT Tensor Core v2](https://arxiv.org/html/2408.06003v2) | 定向核对 §3.1–3.3 的复用、elongated tiling 与编译融合 | LUT 复用和减少搬运已广泛研究；其定制硬件/LMMA 条件不适用于当前 AVX2 CPU。 |
| [FLUTE](https://aclanthology.org/2024.findings-emnlp.724/)，Findings EMNLP 2024 | 正式页与全文入口；本轮仅摘要级筛选，尚未完成设计精读 | 是 LUT 量化权重的 GPU 引擎，不据摘要推断其没有本项目的某项优化。 |
| [FluxBin v1](https://arxiv.org/html/2608.15602v1)，2026 预印本 | 定向核对摘要与 §3.2 的 scale fusion/VCM | 同样关注布局和 LUT 开销，但依赖多二值基量化、CUDA 与稀疏列重映射；不直接移植。 |
| [PolyQ v1](https://arxiv.org/html/2607.14618v1)，2026 预印本 | 定向核对 §4.1–4.3 的 channel permutation/聚类/跨层传播 | 消除布局变换已有编译方案；本实验不改变模型权重和跨层布局，工程范围更小，新颖性也更弱。 |
| [Cache-Oblivious Algorithms](https://www.cs.cornell.edu/courses/cs612/2006sp/papers/frigo99.pdf)，1999 | 摘要与矩阵转置问题筛选；不是全文精读 | 转置的缓存局部性是经典问题。我们的固定 B=16 方案也不是 cache-oblivious 算法。 |

上述是十项来源的定向核对/筛选，**不是十篇全文精读**。原路线的广泛研究选题仍需继续；但当前证据已足以否定“分块转置本身是新贡献”，也足以开展用户指定的工程动机实验，无需为了凑论文数量推迟验证。

## 代码核对

1. 2026-11-17 查询作者 `OpenBitSys/vlut.cpp` 的 master，仍为 `7a813d9c2b6c73d1066eeff49b67794318f682bd`，与保留的原版相同。原版 `ACCUMULATE_TABLE_TRANS` 内层跨输出行读取；没有本候选的 16 行分块 helper。核对位置：[固定版本核心文件](https://github.com/OpenBitSys/vlut.cpp/blob/7a813d9c2b6c73d1066eeff49b67794318f682bd/ggml/src/ggml-cpu/ggml-cpu-quants-vlut.c)。这只说明该版本，不证明其他实现均没有。
2. T-MAC 当前 main 查询 SHA 为 `7042f8f73330bd083bc1e4bc5ccb3f88a4904aee`；已读 [qgemm.py](https://github.com/microsoft/T-MAC/blob/7042f8f73330bd083bc1e4bc5ccb3f88a4904aee/python/t_mac/ops/qgemm.py) 的 `QGeMMLUTBitsCodegen._compute/_schedule`。存在 M/N tile、K split、reorder、cache_write 和向量化；不是可直接复制到 Vec-LUT 的同格式 helper。
3. 不采用 T-MAC 的 `fast_aggregation` 或重新量化模型：这会改变数值语义、模型条件和研究范围。也不安装 TVM、PyTorch-TPP 或 CUDA。

## 最小实验与反证

- 固定正确基线、安全 K 段长、模型、线程和输入；唯一变量为 B=16 的提升遍历顺序，保留独立 memset。
- 先检查 helper 和真实内核的整数等价性，再看 widen 的诊断时间与无插桩 graph 总时间。局部阶段改善不能替代总耗时改善。
- 检查 N=1、尾 tile、多线程小分区，以及全部既有模型形状。工作集局部性只是机制假设；本机无硬件计数，不声称测得 cache miss 下降。
- 若最小动机实验已显示主要场景没有稳定总收益，按停止条件保留负结果、默认关闭，不再用更多调参掩盖失败。若通过，再扩大到完整形状集和真实模型。
- 后续研究选题应建立额外问题/机制证据；本次即使有收益，也只能先称可复现的工程改进。
