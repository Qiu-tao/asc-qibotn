# ASC 选拔作业：QiboTN

- 姓名：邱明涛
- 年级专业：24级计算机科学与技术
- 题目：QiboTN 量子线路模拟优化（CPU）
- 本次报告日期：2026-09-28
- 对应报告：邱明涛_HPL_QiboTN_report.pdf
- HPL 仓库：https://github.com/Qiu-tao/asc-hpl

## 本次提交对应的实验

请查看 [qft_cpu_20260928](qft_cpu_20260928/)。本次报告采用该目录中的 QFT 实验。

CPU：Intel Xeon Gold 6430，容器配额 16 核、120 GiB 内存；AutoDL 租赁实例。GPU 未参与计算。

Python 3.10.8 / QiboTN 0.0.3 / Qibo 0.2.17 / Quimb 1.10.0。完整版本见目录内 requirements.lock.txt。

本次完成 8、12、16 qubit 的 QFT 模拟，比较线程配置、收缩路径策略和批量进程复用。核心对照共 75 次测量，每配置重复五次；最大相对 L2 误差约 4.87e-14，低于预设 1e-10。

| 实验 | 结果与边界 |
|---|---|
| 16 qubit，native，线程 16 → 1 | 中位数 0.239683 s → 0.194041 s；范围有重叠，不声称稳定普适加速 |
| 单线程收缩策略 | greedy 无明确收益；auto-hq 明显变慢 |
| 四任务批量进程复用 | 中位数 8.323671 s → 2.419117 s，约 3.441 倍；属于批量完整流程收益 |

## 核查入口

- [实验说明与计时口径](qft_cpu_20260928/README.md)
- [逐次测量](qft_cpu_20260928/results.csv)
- [统计汇总](qft_cpu_20260928/summary.csv)
- [自动审核](qft_cpu_20260928/audit.json)
- [原始日志](qft_cpu_20260928/logs/)
- [原始 JSON 与参考检查](qft_cpu_20260928/results/)

## 复现

需要 Linux 和 Python 3.10。在新目录中运行，避免覆盖原始记录：

```bash
git clone https://github.com/Qiu-tao/asc-qibotn.git
cd asc-qibotn/qft_cpu_20260928
mkdir ../qft_reproduce
cp benchmark.py run_trials.py summarize.py reproduce.sh requirements.lock.txt ../qft_reproduce/
cd ../qft_reproduce
bash reproduce.sh
```

没有独立 NVIDIA GPU 也可运行；计算后端为 NumPy CPU。线程对照按 16 CPU 配额设计，其他机器应记录实际资源和配置变化。
