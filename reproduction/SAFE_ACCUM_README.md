 > 2026-11-18：自适应实现和旧一键入口已删除，详见 [退役记录](RETIREMENT.md)。以下为历史实验说明。

# 独立安全累加实验：入口与撤销

本分支从稳定提交79db4941派生，只用于P6.3实验。稳定分支仍为repro/cpu，不自动合并。实验选择项默认legacy128；候选adaptive不会被常规构建自动打开。原作者提交与稳定复现源码均保留。

## 本机路径

- 稳定源码：`E:/VecLUT-Repro/src/vlut.cpp`。
- 实验源码：`E:/VecLUT-Repro/experiments/safe-accum/src`。
- 实验构建/日志：`E:/VecLUT-Repro/experiments/safe-accum/builds`、`results`。
- models链接到稳定项目已有GGUF，只读取，不下载/改写。
- legacy128构建链接到稳定项目已有`builds/p6-selected`，不在该目录重新编译，不改旧二进制。它包含此前选择性分块，作为较强旧对照；不是作者错误原版。

依赖沿用WSL Ubuntu-24.04、GCC/G++、CMake、Python标准库、PowerShell 7和Git。没有新增软件、模型格式、GPU或服务器要求。默认构建并行4，性能串行。

## 一键运行

```powershell
E:\VecLUT-Repro\experiments\safe-accum\src\reproduction\run-safe-accum.ps1
# 确认同代码构建及正确性已经通过时：
E:\VecLUT-Repro\experiments\safe-accum\src\reproduction\run-safe-accum.ps1 -ReuseBuild
```

需要已有稳定环境及p6-selected构建，见稳定分支P6_REFINE_METHOD.md；首次克隆本实验分支不等于已具备这个对照。可通过`-DataDirectory`指定独立实验数据根，`-StableDirectory`指定稳定数据根。禁止把两者设成同一个目录；本机默认已分开。

流程：正确性/ASan → 24配置三版本两批筛查 → 按预设门槛选择整模型确认或停止自适应。若自适应门槛失败，单独确认固定240的四组P128模型性能，不把它改写为自适应通过。生成逐样本JSONL/CSV、构建和运行日志、模型及库哈希、自动汇总。

Linux可以依次调用`run-safe-accum.sh`、`experiment_safe_accum.py`；自适应停止后若要固定基线确认，调用`confirm_fixed_accum.py`。`analyze_safe_accum.py RUN [OUTPUT_SUBDIR]`生成统计，使用新输出子目录，不覆盖原分析。

## 放弃/回退

直接继续使用稳定项目原入口即可，完全不需要删除稳定源码中的任何实验代码。所有实验改动仅在此worktree/分支，`git diff 79db4941`列出完整补丁。当前没有自动删除或reset脚本；保留失败数据比删除文件更有价值。

如果以后决定清理磁盘，先保存结果和分支，再单独审核worktree的绝对路径与修改状态；不能对整个E盘项目递归删除。本次未执行清理或合并操作。
