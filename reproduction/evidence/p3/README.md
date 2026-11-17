# P3 Falcon3 公开证据

运行 `p3-20261117-220123-426`，冻结测量代码 `3da36b69b2eb523bc91b0241d5376dbd927d783c`。模型与二进制哈希分别见 model-manifest.json 和 *-binaries.sha256；source.patch、git-status.txt 为空，表示冻结运行开始时源码干净。

- `smoke-*.jsonl` / `.stderr.log`：真实生成、模型逐张量类型及执行日志。normal/profile、B=1/4 都保留。
- `path-verification.json`：正常构建与插桩构建 token 一致、目标函数的确切调用次数。
- `cross-batch-verification.json`：从已保存输出核对 B=4 每条序列与 B=1 的 token IDs 相同；这是测试后附加核验，不在性能计时内。
- `00-…17-*.jsonl` / `.stderr.log`：每个配置的模型初始化信息、一次预热、5 次正式样本及全部输出 token。
- `raw.csv` / `summary.csv` / `measurements.md`：90 个正式样本与统计；不包含预热和 profile 耗时。
- `setups.json`：每个配置的模型加载/上下文耗时、输入 tokens、实际 n_ctx。
- `manifest.json` / `commands.jsonl`：测试配置、顺序、环境与可复用命令。
- `monitor.jsonl` / `quality.json`：WSL 资源监控、波动与换页；18 配置均 CV<5%，无稳态 major faults 或 swap。
- `correctness/`：所用 ggml 库已通过的 P1 证据摘要；完整历史日志在 E 盘对应 P1/P2 目录，不重复运行未改变的内核测试。
- `performance.png`：Prefill 和并行 Decode 曲线；合计吞吐与每序列速度分开。

这份证据只包含日志和测量，不包含 GGUF 权重。模型文件在 E 盘 models/falcon3-1b-i2v4，下载脚本固定唯一文件、revision、SHA256，遵循模型来源声明的许可。公开文本统一 LF 换行，数值和记录不筛选。

完整构建/CMake 配置、下载重试、探针和 quick 运行日志仍在 `E:\VecLUT-Repro\results\`。只复用本系统，不存在其他框架对照结果，也没有优化收益。

本目录的 `evidence.sha256` 不包括它自身；在本目录运行 `sha256sum -c evidence.sha256` 可检查发布文件。
