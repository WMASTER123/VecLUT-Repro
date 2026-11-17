# P6 第二轮：固定 CPU、收益复核与选择性启用

2026-11-18。本轮沿用正确性修复版 OFF 对照，首先复核强制分块 ON，再根据形状证据决定是否增加选择性版本。所有测量在本机 E 盘；不部署其他框架。

## 固定了什么

使用 `taskset` 指定 WSL CPU，并设置一致的 OpenMP places、CLOSE、PASSIVE 和线程数。每个样本记录 `sched_getaffinity`、当前 CPU、迁移计数、Linux runnable wait，以及进程 CPU 时间；单线程若逃离指定 CPU，脚本立即失败。

这固定的是 Linux 虚拟 CPU，不是独占物理 P 核。宿主是 14 核/20 线程的 i7-12700H，WSL 则显示 10 核/20 线程的对称拓扑，不能直接将编号映射为宿主混合核心。保留 Windows 平衡电源方案，不改全局电源、ASLR、安全配置或其他应用的亲和性。后台只读记录宿主 CPU 利用率与系统提供的频率比例；缺少可用 PMU、真实频率控制和 vCPU→物理核心映射，不能声称彻底消除宿主噪声。

依据：[Linux sched_setaffinity](https://www.man7.org/linux/man-pages/man2/sched_setaffinity.2.html)、[GNU OpenMP 绑定说明](https://gcc.gnu.org/onlinedocs/libgomp/OMP_005fPROC_005fBIND.html)、[WSL2 虚拟机架构](https://learn.microsoft.com/en-us/windows/wsl/compare-versions)。这些文档说明机制，不构成本机已绑定正确的证据；本机状态必须实测。

## 逐样本对照

`bench_p3.cpp` 新增可选 stdin RUN 协议，默认关闭，不改变模型算子。OFF/ON 两个进程各加载同一 GGUF，权重页由操作系统按其正常规则共享，分别持有上下文；空闲进程阻塞在 stdin，任意时刻只计算一个版本。加载、预热与性能分开。

每个版本预热一次，随后按 ABBA、BAAB 交替的四样本块执行；每配置至少每版本 6 个正式样本。保留逐样本时间戳、输出 token 和最后 logits 的字节哈希；单线程所有对应样本哈希必须一致。记录 major faults/swap，出现异常立即停止并保留记录。

首轮三组均为 BitNet P128/1线程：旧 OpenMP 环境、显式 CPU0、显式 CPU2。旧配置也实际测量掩码，不预设它“没有绑核”。两个 resident 进程的交错方法与上一轮分进程分批运行不同，因此只能评估新协议的重复性，不能将改善单独归因于 taskset。

[Google Benchmark 的方差说明](https://github.com/google/benchmark/blob/main/docs/reducing_variance.md) 提醒：亲和性、频率、SMT、缓存和后台负载均会影响测量，批内低波动并不保证不同运行间可比。本项目采用进程级控制与交错顺序，不照搬其中会改变全机配置的命令。

## 常见形状及边界

`screen_widen_shapes.py` 筛查六种真实 M/K 形状，N=1/16/32/33/128/256，线程1/4；另加 M=2560/3072/4096、K3200、N32/128 的单线程邻近点，共78配置。各版本五样本，两个相反次序批次，共1560样本。目标150ms是短筛查，不能当成1秒长采样确认；启用决定还需真实模型的较长前向实验。

选择规则应依赖实际线程分区行数、有效token及已验证线程条件，不硬编码模型名称。必须检查正常 Prefill 长度及不整除 tile 的尾块；不能只测巨大矩阵、最佳单样本或人为缩小到缓存中的问题。

## 创新与适用范围的判断标准

当前已进入 P6 微优化阶段。贡献候选是安全累加基础上的提升转置访问顺序，以及避免无益场景的轻量选择规则。三值打包、Vector LUT、INT16/INT32 分级累加属于作者机制；溢出修复属于正确性工作。

[Vec-LUT §3.3–4](https://arxiv.org/html/2512.06443v2) 已包含转换融合、缓存分块与离线参数选择；[LIBXSMM 的形状特化与分派](https://libxsmm.github.io/libxsmm/documentation/libxsmm_tune.html) 也表明按形状选择并非新概念。因此本轮最多先定位为有证据的工程改进，不能宣称首次分块或首次形状感知，也不能用“微创新”替代新颖性证明。

单 CPU 线程上的 Prefill 仍同时处理多个 token，是正常并行输入场景；但它对应单线程资源预算，并不意味着胜过本机四线程的绝对速度。本轮不声称多请求服务、能耗或所有CPU平台都受益。若效果仅存在异常尺寸或无法超过噪声，则不推荐启用。

## 本轮选择性版本

实验开关 `VLUT_I2V4_SELECTIVE_WIDEN` 默认 OFF，并与强制分块开关互斥。当前保守规则：线程数1、T32、线程输出行数≥2560、K≥3072、至少32个token；仅完整tile进入B16 helper，尾tile仍采用基线。K约束排除筛查中大型输出行但K2048的退化，不能只看M。阈值是经验限定，不是宣称精确最优交点；不硬编码模型名，也不自动调优。

OFF/selected/profile/ASan 都跑 P1/P4；额外八个大图边界逐元素比较INT64参考，涵盖阈值两侧、多线程分区、余K与token尾块。helper有180项坐标检查和10项策略检查。profile记录实际选中调用及提升元素数，供覆盖率审查。

模型确认使用BitNet单线程P32/33/128/256，各版本8样本；Falcon单线程P128、BitNet四线程P128、两个模型四线程P32/G8 Decode，各版本6样本，总计112正式样本。1线程固定CPU2，4线程使用0/2/4/6。形状筛查和单线程CPU0/2重复先于此计划；没有挑选一份最快数据替代全部结果。

## 一键入口

```powershell
E:\VecLUT-Repro\scripts\run-p6-refine.ps1 -Stage Selective
# 已完成同代码构建/正确性验收时可复用：
E:\VecLUT-Repro\scripts\run-p6-refine.ps1 -Stage Selective -ReuseBuild
```

公开克隆使用 `./reproduction/run-p6-refine.ps1 -DataDirectory E:\VecLUT-Repro`。`-Stage Affinity`、`-Stage Screen` 复查前两阶段，需要先有 P6 OFF/ON 构建。Selective 默认自动准备本轮构建，复用/校验已有两个GGUF，并先运行诊断路径检查再做无插桩性能。

Linux依次运行 `prepare-selective.sh` 与 `run-p6-refine.sh reproduction/plans/selective.json`，设置 `VECLUT_REPRO_DIR`。PowerShell入口额外记录宿主遥测并在结束时停止自己的监视进程。现有WSL/GCC/CMake/Python标准库即可；没有新的模型格式、训练或GPU依赖。
