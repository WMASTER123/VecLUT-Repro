# P2 公开证据索引

所有测量都仅执行修复后的 I2_V_4。没有其他框架数据、模型下载或优化收益。

| 目录 | 运行 | 代码版本 | 内容 |
|---|---|---|---|
| full | p2-20261117-202258-436 | 438ea26d01e47d495342976eea1c3d8fad93dbb4 | 72 个矩阵/N 组合，normal 1440 行；profile 200 行 |
| confirmation | p2-20261117-203434-396 | 7d55f8d0（完整 SHA 见 source-sha.txt） | 长采样 normal 240 行；拆开清零的 profile 200 行；正确性回归 |

`raw.csv` 是每个重复的原始测量，`summary.csv` 给出中位数/极值/IQR/CV；`manifest.json` 固定输入、随机种子、OpenMP 环境及二进制 hash；`monitor.jsonl` 保留 WSL 内存、交换与负载；`commands.jsonl` 保留实际测试命令。命令里的绝对路径属于本机 E 盘映射，换机器请通过一键脚本生成对应路径。

首轮 full 的 widen 包含提升、转置和清零；confirmation 新增 clear_worker_us，widen 仅含提升转置。**不能不加区分地合并这两列数据。**

首轮 288 配置中 8 个 CV>10%，已全部覆盖于长采样复测，3 个仍高波动。复测 48 配置总计 5 个 CV>10%。不删除异常慢样本，不使用复测前后差值宣称优化收益。

normal 为无插桩性能；profile 为诊断，包含计时扰动；各工作线程份额的和不是总墙钟时间。原始算子输出检查不在计时区域内。所有比例和限制见 [完整报告](../../P2_REPORT.md)。

本机完整配置/构建日志、逐案例 stderr、全部 P1 子进程日志、预跑及失败启动记录仍在 `E:\VecLUT-Repro\results\`；这里发布结构化原始测量、监控、会话日志、P1 摘要/数值日志及图表。`os-supplement.txt` 在测试后补记 OS/Python 版本；后续一键脚本在测试前自动记录这些项目。

环境：i7-12700H，WSL2 Ubuntu 24.04.5，GCC 13.3，CMake 3.28.3，Python 3.12.3；已有 matplotlib 3.6.3 负责可选绘图。CPU Release/native，OpenMP ON，tile=32，weight unroll=16，累加块 K=128；AVX512/SVE/Accelerate/GPU/BLAS OFF。无需额外安装或模型文件。

`evidence.sha256` 校验本目录发布的文件；它不包含自身。使用 `sha256sum -c evidence.sha256` 时在本目录运行。
