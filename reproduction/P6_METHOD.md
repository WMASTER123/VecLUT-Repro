# P6：单项分块提升转置实验

基线是通过 P1/P4 的正确性修复版；实验版仅打开 `VLUT_I2V4_BLOCKED_WIDEN`。默认 OFF。作者错误输出版本不参与性能对照。

## 改动与边界

生产 helper 位于 `ggml/src/ggml-cpu/ggml-vlut-widen.h`，仅由 `ggml_gemm_i2v4_i8v_lut` 的四处提升转置调用。每 16 行内先遍历 token，再遍历行；INT16 有符号提升、INT32 加法、K=128、INT16 缓冲区清零均保留。I1 与其他 I2 仍使用原共享宏。

这是普通局部性改进实验，不是已经证明的新研究贡献。相关文献与已有实现核对见 [LITERATURE_REVIEW.md](LITERATURE_REVIEW.md)。没有添加新的模型、依赖或硬件要求。

## 一键执行

```powershell
E:\VecLUT-Repro\scripts\run-p6.ps1
# 内核实验后追加真实模型 OFF/ON 确认：
E:\VecLUT-Repro\scripts\run-p6.ps1 -WithModels
# 已有合格 P6 OFF/ON 构建时，仅做模型确认：
E:\VecLUT-Repro\scripts\run-p6.ps1 -ModelsOnly
# 其他克隆路径：
.\reproduction\run-p6.ps1 -DataDirectory E:\VecLUT-Repro
```

```bash
VECLUT_REPRO_DIR=/mnt/e/VecLUT-Repro bash reproduction/run-p6.sh
```

构建独立的 OFF、ON、ASan-ON、profile-OFF/ON，正式版本使用与 P2/P3 一致的 Release/native 编译。每个版本先跑 P1 的 164 项与边界、大工作区，以及 P4 的 225 项与 K=4/非法输入；135 项 helper 坐标测试包含 INT16 极值、非零输出初值、canary、尾块和未使用 lane 不变。使用原来的 GCC/CMake/Python 标准库，不自动安装软件。

## 性能口径与计划调整

为先判断方向是否值得展开，首次采用 8 个预先固定的图配置：BitNet 三种主要形状的 N=1/32/128，Falcon 大输出行的 N=33，及 M=17/K=144/N=33 的边界；线程 1/4。具体列表保存在 `run_p6.py` 和每次 manifest。这是原优化方案的最小动机门槛，**尚不是原计划的六形状全 N 扫描**。无稳定净收益或明显回退时停止扩展，保留默认关闭及负结果。

每配置先 OFF→ON，再在第二批反转配置顺序并 ON→OFF；各版本各批 5 个样本，目标每样本 1 秒，共 160 样本。沿用 P2 的校准迭代上限 4096，因此小边界 M=17/K=144/N=33 实际每样本约 0.19 秒，不能将其写成完整 1 秒确认；该组不用于宣称小收益。每次进程中预热、校准、再次预热，并以实际量化激活的 INT64 点积抽查结果。两批位于同一会话，是顺序平衡的重复运行，不声称跨日独立复验。报告中位数、每批延迟比和 CV，保存全部样本。OFF/ON 在同一会话分进程串行执行，无其他编译/基准同时运行。

若近似 1 的比值落在噪声内，不宣称小加速。只有方向在两批稳定且总图耗时受益，才扩展形状与真实模型；helper/分段加速不能代替模型收益。profile 计时另存，只用于解释 widen/clear 的变化，不用于正式速度结论。记录 major faults、swap 页数、可用内存快照；缺少硬件计数器，不能声称已经测到缓存命中率提升。

结果写入新的 `results/p6-*`，包括源码 SHA/patch、CMakeCache、可执行文件和共享库哈希、正确性日志、配对 CSV、分段 CSV、统计和资源快照。不会覆盖旧测量。

## 真实模型确认范围

在内核三个单线程配置出现稳定收益后，直接用两份已有模型检查传播效果：Falcon3/BitNet 各测 P128 Prefill 的 1/4 线程，以及 P128/G16/B1 Decode 的 4 线程。每配置 OFF→ON、ON→OFF 两批，每版本每批预热一次、正式五次，共 120 样本；固定同配置的生成 token 必须相同，另做两模型 OFF/ON smoke。

这是针对性确认，未执行原候选计划的全 N/六形状优化扫描，也未测试优化版 B16 Decode。选择这些负载是为了检验已观测的单线程收益及四线程/短输入限制，不称全场景验证。G=16 与 P3/P4 的 G=32 分开报告，避免混算。模型加载排除，计时仍包括 Decode 的宿主 greedy 选择。

Linux 补充入口为 `bash reproduction/run-p6-models.sh`，它检查既有 OFF/ON 的 Release、无插桩、非 Sanitizer 配置，构建 libllama、重跑同库 P1、校验模型 SHA256 后测量。没有合格构建时先运行 run-p6.sh。使用独立 `latest-p6-models.txt`，不覆盖 P3/P4 基线。
