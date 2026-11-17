# P3：Falcon3 1B / BitNet 3B 真实推理、内核路径与性能

Falcon3 1B 与 BitNet 3B 的 I2_V_4 扩展均已完成。只测本系统，不部署或比较其他框架。下文保留 Falcon3 的具体模型/提示配置；BitNet 差异在本节明确列出。

## BitNet 扩展

PowerShell：`./reproduction/run-p3.ps1 -Model bitnet-3b-i2v4 -DataDirectory E:\VecLUT-Repro`。Linux：`bash reproduction/run-p3.sh --model bitnet-3b-i2v4`。默认仍为 Falcon3，可加 `-Quick` / `--quick`。

模型 registry 固定 revision、大小及 SHA256，已下载文件校验后复用；BitNet I2 文件 916,849,184 字节。模型来源、哈希、真实矩阵形状和 18 配置结果见 [P3_BITNET_REPORT.md](P3_BITNET_REPORT.md)。

BitNet 是基础模型，没有 chat template；功能提示为 `Paris is the capital of France. The city is known for`，生成上限 48 步。182 个 I2 张量、26 层；4 线程一次前向 728 次入口调用。每个目标张量的 M/K 形状在 setup JSONL 中保存；Prefill 最后一层的 FFN 可能因输出位置裁剪而使用小于 P 的实际 N。

两模型均要求同一 B/线程/提示的 normal/profile 生成 token 完全一致。跨 B 或不同序列的文本一致性作为观测记录，不作为通用断言；BitNet 出现该差异后的定位证据见 [BITNET_NUMERICAL_AUDIT.md](BITNET_NUMERICAL_AUDIT.md)。独立整数参考与有限 logits 检查仍保留，正式性能脚本拒绝开启诊断环境变量。

## 环境、模型与一键入口

复用 Ubuntu 24.04 / WSL2、GCC/G++、CMake、Git、Python3 标准库；matplotlib 只用于可选绘图。本机没有安装新包，不需要 GPU、CUDA、PyTorch、Docker。编译并行度默认 4，可设 BUILD_JOBS=2。

```powershell
# 本机已有外层工程
& E:\VecLUT-Repro\scripts\run-p3.ps1
# 快速检查：仍做真实生成/路径验证，性能只测三个配置
& E:\VecLUT-Repro\scripts\run-p3.ps1 -Quick
# 从 GitHub 克隆到 E 盘的独立仓库
.\reproduction\run-p3.ps1 -DataDirectory E:\VecLUT-Repro
```

Linux / WSL：`VECLUT_REPRO_DIR=/mnt/e/VecLUT-Repro bash reproduction/run-p3.sh`。未指定数据目录时使用仓库 `.repro/`。Windows 使用已有 Ubuntu-24.04，其他发行版用 -Distribution 指定。所有构建、模型、日志、临时文件和缓存位于指定目录；不修改 HOME 或全局环境。

模型来源：[XXXXyu/Falcon3-1B-Instruct-1.58bit-vlut-gguf](https://huggingface.co/XXXXyu/Falcon3-1B-Instruct-1.58bit-vlut-gguf)。

- revision：`1cf5c2dc924ab7117053758da68f8376da95fc4d`
- 仅下载：`ggml-model-I2_V_4.gguf`，659,366,272 字节（约 628.82 MiB）。
- SHA256：`6eb67473189b8b6d1a02cdc723b2f284b0e247eba27619c46117fd2d592c6b94`
- 路径：`models/falcon3-1b-i2v4/`；缓存文件通过尺寸与 SHA256 校验后直接复用。部分下载保留 .part 并尝试续传；已有完整文件校验失败则停止、不覆盖。
- 模型采用来源页面声明的 Falcon LLM License，与代码许可证分开。GitHub 发布脚本、模型来源和哈希，不上传 GGUF 权重。

脚本复用 P2 的 builds/p2-normal 和 builds/p2-profile，增加构建作者 libllama，不重复建立整套环境。没有 P2 构建时会自动配置。Release/native CPU、OpenMP ON、tile=32、weight unroll=16、AVX512/GPU/BLAS OFF；复用相同库的 P1 证据，库变化时自动重新回归。

OpenMP：PASSIVE、DYNAMIC=FALSE、PROC_BIND=CLOSE，默认 places `{0},{2},{4},{6}`。这是 WSL 虚拟 CPU 编号，不表示宿主 P/E 核映射。其他机器通过 `-CpuPlaces` / `P3_OMP_PLACES` 指定至少四个可用编号，程序会验证。

## 实际调用和路径证据

`bench_p3.cpp` 是薄测量入口，调用作者 libllama 的模型加载、tokenizer、chat template、KV cache 与 `llama_decode`，底层仍为原项目修复后的 ggml，不重写 Transformer 或 LUT 内核。

每个子进程先读取 GGUF 逐张量类型，确认固定模型有 126 个 I2_V_4 张量；其他类型是 F32、Q4_K、Q6_K，不能声称全部参数均采用 I2_V_4。模型为 18 层、每层 7 个相应矩阵。

功能检查使用模型自带 chat template，问题为 “What is the capital of France? Answer in one short sentence.”，贪心解码，遇 EOG 停止，最长 48 步。分别运行 B=1 和 B=4，normal/profile 均执行；检查输出非空、logits 有限、两种构建的全部生成 token IDs 相同。

profile 构建借助 P2 已有的 `vlut_profile_records[].calls`：进入实际 `ggml_gemm_i2v4_i8v_lut` 才增加计数，且 Prefill/Decode 分开 reset/read。4 线程一次模型前向应有 126×4=504 个工作线程调用；Decode 则乘实际步数。程序检查确切次数，不把类型标签或“能输出文字”当成路径证据。单线程与多线程中的调用次数不同，不等于执行了不同层数。

profile 仅用于路径诊断，不用其耗时报告正式性能。normal 编译关闭插桩，此时计数为 0 代表计数器关闭，不代表未经过该内核。

## 正式测试范围

| 测试 | 参数 | 正式重复 |
|---|---|---:|
| Prefill | P=32/128/256/512；线程 1/2/4；B=1 | 每配置 5 次 |
| 单序列 Decode | P=128；G=32；线程 1/2/4；B=1 | 每配置 5 次 |
| 并行 Decode | P=128；G=32；线程 4；B=4/8/16 | 每配置 5 次 |

共 18 个配置、90 个正式样本。每配置创建新子进程/上下文，先完成一次同负载预热，再计 5 次；每次清空 KV 并重新 Prefill。案例顺序由固定种子 20261117 打乱。预热保留在原始 JSONL，汇总排除预热。

性能输入来自程序中的固定英文文本，重复后截取为精确 P 个 token（包含 tokenizer 添加的特殊 token）；不是随机 token，也不是质量评测集。Decode 使用真实上一轮 logits 贪心选出的 token，固定执行 G 步，性能模式遇 EOG 不提前终止。功能测试则正常尊重 EOG。

并行请求共享同一份 prompt/KV 前缀，解码后每条序列有自己的 KV 路径；不同序列使用相同输入及确定性贪心，所以可能生成相同文本。它衡量共享前缀的固定并发，不代表独立异长请求的在线服务吞吐。一次 Prefill 的分母为 P，不能因为共享给 B 条序列就写成 B×P。

## 计时口径

- **模型加载**：`llama_model_load_from_file` 单独计时，context 初始化单独计时；不进入 Prefill/Decode。启用 mmap，操作系统可能已经缓存文件，且下载校验会读取文件，故不是受控冷盘加载。
- **Prefill**：`llama_decode` + `llama_synchronize`，实际处理 P 个 token，返回最后位置 logits。输入 tokenization、上下文创建和主机贪心扫描在其计时外。P / 秒得到 tokens/s。
- **Decode 模型时间**：逐步累计 decode+synchronize；单独保留，便于和主机开销区分。
- **Decode 主循环时间（主要指标）**：包含 G 次实际模型前向、构造下一批 token、贪心扫描和有限值检查；不含此前 Prefill、文本转换、日志打印。合计吞吐为 B×G/秒；每序列为 G/秒，必须同时报告，不能把合计值称为单请求速度。
- 短生成时首个采样结果来自 Prefill，runner 将这 G 个 token 各送入一次模型前向，所以严格计量 G 个 decode 步骤；不同工具对末 token 是否再前向的约定可能不同。
- `llama_decode` 的任何非零返回均失败；logits 非有限或输出/计数检查不符均停止。

固定 n_batch/n_ubatch=512，KV 为 F16，Flash Attention OFF，GPU offload=0；n_ctx 至少 512，随 (P+G+8)×B 增大，记录实际值。这不是自动最优调参。

## 日志、结果与限制

每次生成 `results/p3-日期-时间-PID/`，保留源版本、diff、构建/配置日志、二进制 SHA、模型 manifest、P1 证据指针。measurements/ 下包含每案例 stdout JSONL/stderr、完整命令、path-verification.json、raw.csv、summary.csv、quality.json、setups.json、图表及每秒 WSL 资源监控。latest-p3.txt 可指向 quick 或 full，使用时核对 manifest。

峰值 RSS 包含模型、KV、图和临时工作区，为进程峰值；mmap/共享页使它不等于独占物理内存。计时重复内的 major/minor faults 单独记录；swap 监控范围是 WSL。报告 CV，保留慢样本，不以最快值代替统计。

上述检查证明指定模型在本机可运行、logits 有限和目标内核被调用；一个问答例子不证明模型质量、量化精度或所有输入正确。尚未测试长上下文、服务延迟分位数、功耗、I1、BitNet 3B 或优化收益。
