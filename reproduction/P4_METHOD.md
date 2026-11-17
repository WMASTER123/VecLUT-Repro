# P4：I1_V_2 的独立验收方法

范围仅为 I1_V_2；不能外推 I1_V、I1_V_4 或所有 I2 变体。复用作者系统，但打包解码、INT64 参考计算、测试驱动和证据采集为本项目补充。

## 一键运行与依赖

```powershell
# 本机已设置根目录 E:\VecLUT-Repro
E:\VecLUT-Repro\scripts\run-p4.ps1
# 可选：完整 18 配置模型测试
E:\VecLUT-Repro\scripts\run-p4.ps1 -Full
```

公开仓库使用 `./reproduction/run-p4.ps1 -DataDirectory E:\VecLUT-Repro`；Linux 使用 `VECLUT_REPRO_DIR=/mnt/e/VecLUT-Repro bash reproduction/run-p4.sh`。默认六组四线程代表配置，`--full` 为与 P3 相同的 18 组，`--quick` 为三组短测试。三种模式都先执行数值与 Sanitizer 检查，不跳过验收。

依赖仍是已有 WSL Ubuntu 24.04、GCC/G++、CMake、Git、Python3 标准库；matplotlib 可选，仅作图。无需新增 CUDA、PyTorch、TVM 或训练环境。脚本将缓存、临时文件、build、模型和日志都放在指定项目根目录。

模型固定在 `model_registry.py`：同一 BitNet revision 的 I1/I2 两个文件，总计约 1.67 GB；已有文件按 SHA256 复用。I2 文件用于检查两种打包是否表达相同权重，不运行外部框架。运行后的 E 盘指针是 `results/latest-p4.txt` 与 `latest-p4-correctness.txt`。

## 顺序与检查

1. `run-p4.sh` 先复用 `builds/asan`，执行 I2 的 P1 回归，再执行 `test_p4.cpp`。ASan/UBSan 错误会终止，不用 Sanitizer 时间作为性能结果。
2. 公用模型脚本构建 normal/profile，分别再执行 P1 和 P4。I2/I1 入口计数使用不同字段，不能将 I2 的计数误报成 I1。
3. `compare_model_packings.cpp` 比较两份 GGUF：全部非 Vec-LUT 张量字节一致；每个三值矩阵选第一、第二、中间、最后行及 32 个固定伪随机行（去重），逐行完整解码所有 K。它是广覆盖抽样，不声称全量扫描所有三值权重。
4. 使用实际 libllama、tokenizer、KV cache 和模型图执行 B=1/4 的生成，验证 normal/profile 输出一致、有限 logits、目标张量类型与真实 I1 调用次数。
5. 性能模式关闭插桩、固定输入、预热一次、重复五次，加载与计算分开记录。默认 Prefill P=32/128/512，Decode P=128/G=32/B=1/4/16，均四线程；线程 1/2/4 的数值正确性已在小矩阵图测试中覆盖。未运行的其他性能配置不得写成已测。

计时分母、共享前缀和 EOS 规则与 [P3_METHOD.md](P3_METHOD.md) 一致。BitNet 跨批量 token 可能不同，原因与边界见 [数值审查](BITNET_NUMERICAL_AUDIT.md)；跨批量一致性是显式观察，不是整数内核的正确性判据。

## 独立正确性覆盖

`test_p4.cpp` 有 225 项常规检查，另以独立进程测试 K=4 计算图、5 项非法输入拒绝。范围包括：

- 所有 243 种五元组三进制模式、所有 81 种四元组尾部模式的独立解码、写入长度和 canary。
- 单独检查 mixed g=5/g=4 的张量行步长与连续性，避免“直接内核可跑、框架却拒绝”的遗漏。
- 直接生产内核与 INT64 参考比较，覆盖负值、全零权重、±127/−128 极值、K 累加边界、N=1/31/32/33/65 及目标 K=3200/8640。
- 图级检查 1/2/4 线程、不均匀 M=7、跨 tile、多切片，工作区预先填入非零值，检查有效输出与边界保护。
- 参考使用同一 INT8 激活与 scale，把量化误差和 LUT 算术错误分开。整数路径要求精确一致，不以大容差掩盖溢出。

原版与修复前状态的反例运行单独保留。`check_p4.py --counterexamples` 只用于记录预期失败；正式脚本绝不把这一模式用作修复版验收。原始一次测试在 K=4 图断言处中止，之后将其隔离成独立子进程，保留首轮中止日志，并用同一 225 项集合做修复前后比较。

## 代码审查要点

- K 段必须是 20 的倍数，才能保持五元组分组和四元组尾部的位置。当前 160 是保守安全选择，不宣称最大允许值。
- 最坏 INT16 部分和为 160×128=20480；INT32 以 `K <= INT32_MAX/128` 约束。任意符号序列的前缀绝对值也不超过这个界。
- g=4 的零向量索引为 40；g=5 为 121。不能把字节 0 当成零权重组合。
- 线程行起点是 floor(ith×M/nth)，不能以 ith×本线程行数替代；两者仅在均匀分配时相同。
- 元数据 row stride/contiguity 修复局限于 I1_V_2。没有更改 GGUF 的权重字节、量化精度或其他格式的核心实现。
