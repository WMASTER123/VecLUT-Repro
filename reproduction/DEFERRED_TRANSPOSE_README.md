# 独立布局实验入口

本分支从稳定正确性修复版 `79db4941` 派生。作者原版、稳定版、旧自适应历史均保留；旧自适应已从其分支最新代码删除。此目录不包含自适应实现。

先读 [预注册方案](DEFERRED_TRANSPOSE_PROTOCOL.md)，最终状态以 [报告](DEFERRED_TRANSPOSE_REPORT.md) 为准。开关默认OFF，固定K240是两版本共同对照条件，不把其收益归入布局优化。

本机 Windows PowerShell 一键入口：

```powershell
& E:\VecLUT-Repro\experiments\deferred-transpose\src\reproduction\run-deferred-transpose.ps1
```

脚本依次构建两版Release和候选ASan/UBSan、执行I2/I1正确性、图级筛查；过门后自动跑模型，未过门即停止。每次新建结果目录，禁止覆盖旧结果。可用 `-Stage build` 仅构建和正确性。

Linux/WSL：

```bash
VECLUT_STABLE_DIR=/mnt/e/VecLUT-Repro \
VECLUT_EXPERIMENT_DIR=/mnt/e/VecLUT-Repro/experiments/deferred-transpose \
bash reproduction/run-deferred-transpose.sh all
```

依赖复用现有Ubuntu24.04、GCC13、CMake、Python3标准库、Git、OpenMP、util-linux/taskset，无pip/GPU/新增模型下载。`VECLUT_STABLE_DIR/models` 应已存在注册的Falcon3 1B和BitNet3B I2 GGUF；模型读前SHA256校验。两个模型对照worker同时驻留、逐样本串行运算；当前12GB WSL内存够用，日志校验swap/major fault。

结果在实验根的 `results/latest-build.txt` 和 `results/latest-experiment.txt` 指向的目录。完整一键流程会自动生成 decision.json 和 MEASUREMENTS.md；需要重新分析已有日志时运行：

```bash
python3 reproduction/analyze_deferred.py /absolute/path/to/experiment-run
```

不应对候选构建使用原目录的稳定一键脚本。回到 `E:/VecLUT-Repro/src/vlut.cpp` 即使用未改变的稳定版本。若候选被删除，本README会标记退役并取消当前运行入口；历史源码可通过实验提交读取，不重写Git历史。
