# QiboTN CPU 量子线路模拟实验

姓名：邱明涛；年级专业：24级计算机科学与技术。
实验日期：2026-09-28；题目：ASC 选拔作业 QiboTN 大题。

本目录是 ASC 选拔作业 QiboTN 大题的独立实验材料。实际数值以 `audit.json`、`summary.csv` 和原始日志为准。报告由 AI 协助编写、运行和整理；提交者需理解实验并按学校要求披露辅助方式。

## 实验范围

- CPU: AutoDL 容器，Intel Xeon Gold 6430；容器 CPU 配额 16 核，内存配额 120 GiB。
- 资源来源：AutoDL 租赁实例，费用账单未采集。附带 RTX 4090（24564 MiB 显存），未用于本次计算；硬件清单见 logs/gpu_inventory.log。
- Python 3.10.8；QiboTN 0.0.3、Qibo 0.2.17、Quimb 1.10.0。全部依赖见 `requirements.lock.txt`。
- 使用 QiboTN 官方发布包的 `qutensornet` / `QuimbBackend`，计算后端 NumPy。
- 强制隐藏 GPU；禁用 MPI、NCCL、MPS 截断，完整输出 complex128 状态。
- Workload: 固定随机种子的 RY/RZ 输入制备 + 链式 CNOT + 官方 `QFT(n, with_swaps=True)`。输入制备使测试不局限于 QFT 的平凡全零输入。
- 主实验规模 8、12、16 qubit；每个输入对应唯一 QASM SHA256。

## 三类优化尝试

1. CPU/BLAS 线程上限：16（分配资源上限基准）、4、1；其余条件相同。
2. 收缩路径策略：固定单线程，原生路径策略与 `greedy`、`auto-hq` 对照；不修改线路。`benchmark.py` 的 `install_optimizer` 显式替换 QiboTN 的收缩调用，保留 QASM 解析和 `DRC` 化简，未修改安装包文件。
3. 批量运行：固定单线程和原生策略，对同样的 8、10、12、14 qubit 四项任务比较每项启动新进程与一个进程依次执行。每次重新建立线路并计算完整状态；不缓存答案。

## 测量与正确性

主实验共 3 个规模 × 5 个配置 × 5 次重复 = 75 个测量值。固定种子打乱执行顺序，各次在独立子进程中先运行 6 qubit 预热，再测目标线路。`execute_s` 从后端执行开始到完整状态返回，包含 QASM 转换、网络建立、化简、路径搜索和收缩；不包含导入、输入线路建立、参考结果加载、误差检查和保存。所有配置口径一致。

`process_wall_s` 是父进程计时，包含启动、导入、预热、验证、退出等；它与 `execute_s` 不可混用。首次 smoke 测试含首次编译等开销，只用于安装/正确性检查，不作为优化基准。

批量实验每种模式重复 3 次，交替执行顺序。批量时间包括进程启动、导入、计算、验证、日志与 JSON 保存；它表示完整验证流程的吞吐量，不表示单线路核心计算加速。

参考解采用 Qibo `NumpyBackend` 稠密模拟，并与 `sqrt(2**n) * numpy.fft.ifft(prepared_state)` 交叉验证 QFT 约定。每次 QiboTN 输出验证：有限数、形状、complex128、相位对齐后的相对 L2 误差 ≤ 1e-10、范数误差 ≤ 1e-10。保真度仅为辅助指标。另有故意扰动后重新归一化的错误状态，确认验证器能拒绝“归一化但算错”的输出。

`maxrss_mib` 是整个 worker 进程到该时刻的峰值 RSS，包含导入、参考态、预热和验证；不是单次张量收缩独占内存。云主机可能有其他租户，结果不代表独占物理 CPU 性能，也不外推到其他线路或更大规模。

## 文件与验收入口

- `audit.json`：核验汇总，完成性、错误、真实线程池、输入哈希。
- `summary.csv`：各组中位数、最小/最大值、标准差、误差及相对 native16 的加速比。
- `results.csv`：75 次目标规模的逐次记录，含运行命令及 QASM 哈希。
- `results/manifest.jsonl`：每个子进程的命令、时间、退出状态。
- `results/reference_checks.json`：FFT 交叉验证与错误结果负对照。
- `results/kernel_*.json`：每次完整测量；首个 6 qubit 条目为预热，末个为目标。
- `results/batch_summary.json`：批量流程逐次记录。
- `results/profile_*.json`：单次分阶段诊断，不当作五次统计结果。
- `results/environment.json`、`requirements.lock.txt`：资源及软件环境。
- `logs/`：原始安装、执行及审核日志。
- `references/`：独立参考状态，用于复核。
- `vendor/`：官方 QiboTN 发布轮子及来源记录。

## 从干净目录复现

在 Linux 和 Python 3.10 环境中，将 `benchmark.py`、`run_trials.py`、`summarize.py`、`reproduce.sh`、`requirements.lock.txt` 复制到一个新目录，然后执行：

```bash
bash reproduce.sh
```

已有结果目录拒绝直接重跑，防止覆盖证据或将两轮记录混在一起。硬件不同可能得出不同性能结论，但正确性应通过。资源小于 16 CPU 时应修改线程实验设计并明确记录，不能冒充原实验复现。

快速查看一次已有实验：

```bash
.venv/bin/python benchmark.py --mode worker --qubits 6 16 --threads 1 --optimizer native --output results/manual_check.json
```

此命令需要已有 `references/`。快速检查结果不自动纳入原来的统计。

## 提交范围

本目录对应合并报告中的 QiboTN 部分。HPL 使用 https://github.com/Qiu-tao/asc-hpl 中的历史运行记录。最终 PDF 文件名为 邱明涛_HPL_QiboTN_report.pdf，邮件仅附 PDF；本目录提供源码、原始日志和复现依据。

## 来源

- 作业：https://github.com/DotRedstone/asc-selection-homework/blob/main/docs/assignment.md
- QiboTN：https://github.com/qiboteam/qibotn
- 官方文档：https://qibo.science/qibotn/stable/getting-started/quickstart.html
- PyPI 固定发布版：https://pypi.org/project/qibotn/0.0.3/

实验使用发布版 0.0.3，不混用仓库 main 的新接口。可见网页的 stable 版本号不能替代已安装包的版本检查。
