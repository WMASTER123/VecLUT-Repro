# P2：仅 I2_V_4 的 CPU 内核测量

## 一键入口

本机已有 WSL Ubuntu 24.04、GCC/G++ 13.3、CMake 3.28、Git、Python3，直接复用。可选 matplotlib 仅画图；没有它也会生成 CSV 和 Markdown。不需要模型、GPU、PyTorch 或额外框架，不自动安装软件。

Windows PowerShell（仓库在 E 盘）：

```powershell
.\reproduction\run-p2.ps1 -DataDirectory E:\VecLUT-Repro
# 8 个矩阵/N 组合的入口检查
.\reproduction\run-p2.ps1 -DataDirectory E:\VecLUT-Repro -Quick
# 12 个组合，1 秒采样，覆盖正式首轮出现高波动的形状
.\reproduction\run-p2.ps1 -DataDirectory E:\VecLUT-Repro -Confirm
```

本机外层快捷入口是 `E:\VecLUT-Repro\scripts\run-p2.ps1`。Linux / WSL：

```bash
VECLUT_REPRO_DIR=/mnt/e/VecLUT-Repro bash reproduction/run-p2.sh
```

默认输出到仓库 `.repro/`；显式指定目录后构建、日志、绘图缓存、Python 缓存、临时文件都位于该目录。每次生成新 run-id，不覆盖旧结果。`results/latest-p2.txt` 指向最近一次运行，但它可能是快速或确认运行，应同时查看 manifest 的 suite。

默认 OpenMP `PASSIVE / DYNAMIC=FALSE / PROC_BIND=CLOSE`，places 为 `{0},{2},{4},{6}`，只是本机 WSL 的虚拟 CPU 编号，**不代表宿主 P/E 核映射或四个不同物理核**。其他机器先用 `taskset -pc $$` 查看允许编号，然后通过 PowerShell `-CpuPlaces '{0},{1},{2},{3}'` 或 Linux `P2_OMP_PLACES='{0},{1},{2},{3}'` 修改。保留真实配置；不可把不同绑定设置的数据直接作为优化对照。

## 测什么

`bench_p2.cpp` 直接调用实际 I2_V_4 打包、量化、内核和 ggml 图。专用入口避免作者综合测试中 Q4/TQ/I1 路径，不测其他系统。

| 名称 | 输出 M | 输入 K |
|---|---:|---:|
| falcon_square | 2048 | 2048 |
| falcon_up | 8192 | 2048 |
| falcon_down | 2048 | 8192 |
| bitnet_square | 3200 | 3200 |
| bitnet_up | 8640 | 3200 |
| bitnet_down | 3200 | 8640 |

维度来自作者 `tests/test-vlut-gemm.cpp` 中 Falcon3/BitNet 层形状。权重为固定种子生成的三值，激活为确定性 INT8 可表达值；**不是加载真实模型权重**。N 是一次矩阵运算的 token/列数，覆盖 1/8/16/31/32/33/63/64/65/128/256/512。

- graph：单个 `ggml_mul_mat`，线程 1/2/4，计时包含激活量化与重排、线程同步、实际内核、内部 malloc/free 和输出缩放，不包括图创建、输入生成和权重打包。
- direct：串行调用同一个生产内核，激活提前量化；包含内核内部临时分配。不是另一个框架，也不等于完整模型。
- 216 个 graph 配置 + 72 个 direct 配置，各 5 个重复样本，共 1440 行正式原始数据。
- 每配置先预热 3 次并校准迭代数，每个重复切换配置后再预热 1 次。每样本目标 300 ms，迭代数限制 1…4096；实际时长可能因漂移变化，以日志为准。
- 每个重复轮转四种配置的顺序，矩阵案例按固定种子打乱；不挑选最快值作为结论。报告中位数、min/max、IQR、CV。CV 超过 10% 标记高波动。
- 每配置测量前及每个重复之后抽查 64 个输出坐标，用相同量化激活的 INT64 点积作参考；检查不进入计时。抽样不是全矩阵正确性证明，P1 独立回归负责小矩阵与极值边界。

指标是 µs/次、runs/s；`ns_per_effective_mac` 只是按逻辑 M×K×N 归一化，不能当成执行了这么多乘法。**不能将 runs/s 或 N×runs/s 写成整模型 tokens/s。**

## 编译与正确性门槛

Release、native CPU、TABLE_ENTRY_SIZE=32、WEIGHT_UNROLL_BLOCK=16、AVX512/SVE/Accelerate/GPU/BLAS 关闭。normal 和 profile 使用独立目录，先全部构建，再串行测量，避免编译争抢资源。

任一库或 P1 测试源码改变，先重新执行 P1：164 个检查、5 个拒绝用例、大工作区真实计算。通过后才计时；相同二进制复用已保存的回归证据。二进制和库 SHA256、CMakeCache、代码 SHA、diff、命令及退出状态都有记录。正式分享应采用已提交的代码版本；untracked 列表本身不包含文件内容。

## 分段诊断

`VLUT_PROFILE=OFF` 为默认，宏展开为空，不在正式内核加入计时调用。ON 只用于本项目串行执行的诊断；每个工作线程写自己对齐的 128 字节槽，最多 256 线程。多个图同时运行不受支持；reset/read 必须在执行停止后进行。不要把这个诊断接口用于并发服务。

分段为 alloc_init（分配及初始清零）、build（LUT 建表）、lookup（查询及 INT16 加法）、widen（提升 INT32、转置写入）、clear（块间清零）、output（缩放输出）、free、activation（量化及 padding）。`widen` 并非纯类型转换，`alloc_init` 并非纯 malloc。版本说明：首轮冻结提交 438ea26d 将 clear 计入 widen；后续详细诊断将两段拆开，原始 CSV 是否有 clear_worker_us 可区分两种模式，禁止混作同一种字段。

诊断使用 10 个代表案例，每个配置 5 次，目标样本 300 ms（首轮合并计时版本为 50 ms）；核对实际内核调用次数等于迭代数×线程数。细粒度 clock_gettime 会扰动执行，所以百分比仅用于粗定位。多线程字段是各线程**墙钟经过时间之和**，含抢占影响，不是 CPU 指令周期，也不等于关键路径或总墙钟时间。默认图只展示单线程份额。

`--confirm` 的 normal 部分固定两个方阵 N=1/16/31/63/64/512、每组 5 次、每样本目标 1000 ms。这覆盖首轮完整运行中全部 8 个 CV>10% 的配置，同时保留其他线程/模式作为观察；复测不覆盖首轮原始值。程序在创建结果目录前检查 CPU places 的合法性，避免无效绑核参数被运行库静默忽略。

没有可用 perf 硬件计数器时，不宣称测得 cache miss、带宽饱和或确切降频原因。线程收益与尾块成本依靠未插桩结果判断，诊断份额用于解释而非宣称优化收益。

## 日志与资源

`results/p2-*/` 包含 session.log、配置/构建日志、环境、源码状态、二进制哈希、P1 证据指针；normal/profile 子目录包含每案例 CSV/stderr、命令 JSONL、manifest、完整 raw.csv、summary.csv、quality.json、measurements.md、complete.json。monitor.jsonl 每秒记录 WSL 可用内存、swap 计数、CPU ticks 和负载。绘图在运行根目录。

进程峰值 RSS 包含用于独立参考的浮点权重、输入和上下文，不能当成压缩模型或纯内核最低内存。缺页计数是计时区间，监控换页是整个 WSL；Windows 宿主争用仍可能不可见。

运行失败非零退出，并保留之前日志。不自动清理、不自动下载、不修改系统电源策略或 WSL 设置。高波动不等于计算错误，但不应用来主张很小的性能收益。
