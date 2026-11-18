# P6.5 当前入口与依赖

本分支 `exp/valid-lanes-20261118` 的新尾块候选已经退役。当前生产源码与连续INT32父版本638807a1一致，保留额外边界测试、诊断工具和失败证据；默认不启用任何新尾块路径。先看 [最新报告](VALID_LANES_REPORT.md) 和 [自审](VALID_LANES_REVIEW.md)，不要把旧P6.4报告当作本轮通过结论。

## 一键查看已存结果

在PowerShell运行，无需下载模型或启动WSL：

```powershell
& 'E:\VecLUT-Repro\scripts\run-p65-review.ps1'
# 其他克隆位置使用仓库内入口：
& '.\reproduction\run-phase-review.ps1' -Stage Evidence
```

该命令读取公开存档并打印门槛结果，**不是重新运行性能测试**。所有原始数据见`reproduction/evidence/p65`，`evidence.sha256`可逐项校验。

## 本机原样复核和阶段诊断

```powershell
& 'E:\VecLUT-Repro\scripts\run-p65-review.ps1' -Stage Recheck
& 'E:\VecLUT-Repro\scripts\run-p65-review.ps1' -Stage Diagnose
```

Recheck严格复用`experiments/deferred-transpose`的旧二进制，使用其`results/review-20261118/binary-hashes.json`校验，并复用固定模型文件及注册SHA256。它是本机既有布局的精确二进制复核，**不能在任意新克隆直接执行**；没有旧二进制时应依据`DEFERRED_TRANSPOSE_README.md`另建同源版本并明确标为重新构建，不能冒称bit-identical复核。

Diagnose依赖已有`builds/p6-safe240`、`builds/p6-deferred`和上述模型实验布局，另建`profile-*`，只做阶段诊断；不要与其他性能测试并发。结果每次新时间戳，临时数据、cache、build、结果均在E盘。原样复核脚本有一次高CV追加上限，追加后仍不稳定就报告未通过，不循环尝试到成功。

依赖复用本机Ubuntu 24.04 WSL2、GCC/G++13、CMake、Python3标准库、Git、taskset、OpenMP；无需新pip包、GPU、训练或模型下载。本轮使用AVX2、T32、unroll16，两版均K240。固定虚拟CPU不等于物理P核独占。环境记录在`evidence/p65/review/environment.txt`。

## 保留的边界测试

`test_p1.cpp --valid-lanes`是通用尾部正确性测试的命令参数，不是启用已删除优化的开关。它在未修改deferred二进制上也通过1612项检查。可用现有`compile-test.sh`链接保留版后执行；独立INT64参考、所有余数、极值、非零padding与多slice都保留。

原型历史提交`c5c8a53e`用于审计，当前分支已删除其生产实现与专用性能入口。历史构建产物只在E盘保留用于核验，没有上传模型、二进制、缓存或凭据；不要将其当作当前可用优化。不要在稳定或作者worktree恢复失败原型。
