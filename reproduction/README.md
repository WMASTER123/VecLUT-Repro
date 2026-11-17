# Vec-LUT CPU 复现：P1 正确性验证

本目录是基于作者代码的复现实现，不是原作者发布的官方修复。作者项目、MIT 许可证和提交历史均保留。

- 论文：[Vec-LUT，MobiSys 2026](https://arxiv.org/html/2512.06443v2)
- 原版：[OpenBitSys/vlut.cpp](https://github.com/OpenBitSys/vlut.cpp)，固定 SHA `7a813d9c2b6c73d1066eeff49b67794318f682bd`
- 开发分支：`repro/cpu`
- 范围：I2_V_4 打包、激活量化、整数查表内核、CPU 计算图；不下载模型、不训练、不运行其他系统的对比实验。

## 依赖与硬件

实际验证环境：Ubuntu 24.04 / WSL2、GCC/G++ 13.3、CMake 3.28.3、Git、Python3 标准库，i7-12700H CPU。无需 GPU、CUDA、PyTorch、Conda 或 Python 第三方包。

首次构建建议 4 个任务；普通测试矩阵最大约十几 MB，上下文每次分配后释放。建议为编译准备至少 4 GB 可用内存和数 GB 磁盘余量，Sanitizer 构建需要更多余量；这些是工程建议，不是测得的最低门槛。若资源紧张，设置 `BUILD_JOBS=2`。

Linux 若缺少依赖，可自行执行：

```bash
sudo apt-get update
sudo apt-get install build-essential cmake git python3
```

已有这些工具就不需要重复安装。一键脚本只检查依赖，不自动执行 sudo 或下载环境。Windows 复用现有 WSL，先把仓库放到 E 盘；不要在 C 盘克隆。

## 获取代码与一键运行

在 Linux / WSL 中：

```bash
git clone --branch repro/cpu https://github.com/WMASTER123/VecLUT-Repro.git
cd VecLUT-Repro
bash reproduction/run-p1.sh
```

Windows PowerShell 中，也可在仓库目录执行：

```powershell
.\reproduction\run-p1.ps1
```

默认使用现有 `Ubuntu-24.04`，其他发行版通过 `-Distribution` 指定。Windows 不需要运行 .exe 编译产物，测试程序在 WSL 内运行。

已有外层项目目录时，可用 `-DataDirectory E:\VecLUT-Repro` 复用其中的构建和结果路径，避免新建第二套缓存。

默认所有新数据在仓库的 `.repro/`（已 gitignore），因此仓库在 E 盘时构建、缓存、临时文件和结果也在 E 盘。Linux 可通过 `VECLUT_REPRO_DIR` 改用专用数据目录，避免与源码混放。脚本不修改 HOME 或全局缓存配置。

### 同时重现作者反例

```bash
bash reproduction/run-p1.sh --with-baseline
```

或 PowerShell：

```powershell
.\reproduction\run-p1.ps1 -WithBaseline
```

脚本为作者固定提交建立独立、只读使用的 Git worktree，并分别构建。原版测试出现预期反例属于“成功重现错误”；开发版任何数值错误都令脚本非零退出。不会修改作者分支或对作者提 issue/PR。

### 内存与未定义行为检查

```bash
P1_SANITIZE=ON bash reproduction/run-p1.sh
```

PowerShell：`./reproduction/run-p1.ps1 -Sanitize`。使用单独 `builds/asan`，不覆盖普通构建。Sanitizer 不等于证明不存在所有并发错误，也不能用于正式计时。

## 测试分层与判定

| 层 | 实际调用 | 判定 |
| --- | --- | --- |
| 打包 | 作者 `quantize_i2_v_4` | 81 种四元组、多个 K tile，独立逐位解码精确一致 |
| 量化 | 作者/修复版 `quantize_row_i8_v_tile` | 零、全负、负峰值占优、正常正值、微小与大幅值；重建误差不超过量化步长界限 |
| 整数内核 | 实际 `ggml_gemm_i2v4_i8v_lut` | 直接提供相同 INT8 激活，以 INT64 标量点积为 oracle；这些小矩阵要求输出精确相同 |
| 框架集成 | 实际 `ggml_mul_mat` → `ggml_graph_compute` | 同一量化函数产生参考激活，再标量累加，避免将量化误差误诊为索引错误 |
| 内存/边界 | 工作区容量、保护字节、非法 K 子进程 | 无覆盖保护字节；不支持 K 明确 GGML_ASSERT；大 K 的实际执行另测 |

主要覆盖：K=16…2560，N=1/2/8/16/31/32/33/63/64/65，非整齐的 M=1/3/5/7/81，线程 1/2/4，INT8 极值 +127/-128、零权重、多个激活切片。K=16384 用于工作区规划和单 token 实际执行。

所有数值数据在程序内生成，固定公式，无随机种子漂移。`test_p1.cpp` 不复制生产内核，仅实现独立标量参考和测试数据构造。通过源码 API 调用实际生产函数，不用“重写一个正确函数”冒充验证作者代码。

## 输出与恢复

每次运行生成新的 `results/p1-日期-时间-PID/`：

- `session.log`、`configure.log`、`build.log`：执行记录。
- `source-sha.txt`、`working-tree.patch`、`git-status.txt`：实际代码状态。
- `CMakeCache.txt`、`binaries.sha256`：编译配置和文件哈希。
- `fixed/tests.log`、`fixed/summary.json`：修复版详细结果和退出码。
- 可选 `author/`：原版的反例与摘要。

`results/latest-p1.txt` 指向最新运行。脚本不会清空旧结果，不下载模型。未提交的文件不包含在 Git diff 中；分享结果时应使用已提交的版本，并同时保留测试脚本。

## 修复边界

修复原因和反例见 [P1_REPORT.md](P1_REPORT.md)，系统讲解见 [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md)。

本阶段的 INT16 安全累加修复和 K 形状约束针对 **I2_V_4**。其他 I1/I2 变体仍须独立验证，不能把 P1 通过扩大成全部格式通过。共享激活量化/图分发修复会影响这些格式，P4 要检查它们的回归。

真实模型质量、Prefill/Decode 吞吐、性能代价和优化收益均不在 P1 结论内。后续性能基线应采用通过正确性检查的版本，保留作者原始错误输出作为诊断记录。
