# 大题仓库 — QiboTN

> ⚠️ 这是一个模板，推到 GitHub 前请把「姓名/环境/日期」等占位信息补上。

## 基本信息（作业要求：姓名、对应题目、运行环境、复现方式）

- **姓名**：（待填）
- **题目**：大题 — QiboTN（基于张量网络的量子电路模拟）
- **日期**：（待填）
- **机器环境**：见 `env_info.txt`（由 `collect_env.sh` 生成）
- **软件版本**：Python 3.10+，qibo（pip 安装），qibotn（pip 安装），quimb

## 复现方式

```bash
# 1. 建虚拟环境 + 安装 qibotn
bash setup_qibotn.sh

# 2. 运行 Baseline（默认 n=20 量子比特，depth=8）
bash run_baseline.sh

# 3. 其他规模 / 开启 MPS 对比
bash run_baseline.sh 24 10 --mps
```

## 关键文件

| 文件 | 说明 |
|---|---|
| `setup_qibotn.sh` | 建 venv + 装 qibotn |
| `baseline_qibotn.py` | Baseline 脚本：numpy 参考 + qibotn 稠密张量网络 +（可选）MPS，含正确性校验 |
| `run_baseline.sh` | 运行并 `tee` 保存日志 |
| `logs/` | 运行日志（.log）与结构化结果（.json） |
| `env_info.txt` | 机器环境信息 |

## 结果记录

每个运行会在 `logs/` 生成两个文件：
- `.log`：原始输出（命令、时间、机器信息、PASSED/FAILED）
- `.json`：结构化结果（各后端耗时、保真度）

### 结果汇总表（2026-08-27 实测，AutoDL 西B区，CPU 16核）

随机电路（n=20，depth=8，seed=42），日志见 `logs/`。

| 后端 | 时间(s) | 保真度(vs numpy) | 备注 |
|---|---|---|---|
| numpy 精确态矢量（参考） | 8.08 | — | 2^20=104万维，指数级 |
| qibotn 稠密张量网络（quimb） | 11.31 | 1.000000 | Baseline |
| qibotn MPS | 6.07 | 1.000000 | 低纠缠时更优 |

**观察**：20 比特时精确态矢量与张量网络耗时同量级；MPS 对随机电路在此规模最快且保真度 1.0。
后续可在大规模（如 24+ 比特）验证张量网络相对精确模拟的可扩展性优势（精确模拟随比特数指数增长）。

## 优化方向（后续填充）

- [ ] 更大规模下张量网络 vs 态矢量 的可扩展性对比
- [ ] MPS 模式（低纠缠电路加速）与截断误差分析
- [ ] 收缩顺序/优化器设置对耗时的影响
