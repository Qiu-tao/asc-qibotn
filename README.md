# 大题仓库 — QiboTN

## 基本信息（作业要求：姓名、对应题目、运行环境、复现方式）
- **姓名**：邱明涛
- **题目**：大题 — QiboTN（基于张量网络的量子电路模拟）
- **日期**：2026/8/27
- **机器环境**：见 `env_info.txt`（由 `collect_env.sh` 生成）
- **软件版本**：Python 3.10+，qibo 0.2.23（pip），qibotn（pip），quimb 1.12.0

## 复现方式
```bash
# 1. 建虚拟环境 + 安装 qibotn
bash setup_qibotn.sh
# 2. 运行 Baseline（默认 n=20 量子比特，depth=8）
bash run_baseline.sh
# 3. 其他规模 / 开启 MPS 对比
bash run_baseline.sh 24 6 --mps
```

## 关键文件
| 文件 | 说明 |
|---|---|
| `setup_qibotn.sh` | 建 venv + 装 qibotn |
| `baseline_qibotn.py` | Baseline 脚本：numpy 参考 + qibotn 稠密张量网络 +（可选）MPS，含正确性校验 |
| `run_baseline.sh` | 运行并 `tee` 保存日志 |
| `logs/` | 运行结果（.json 结构化结果；经 run_baseline.sh 运行会同时产生 .log） |
| `env_info.txt` | 机器环境信息 |

## 结果记录（2026-08-27 实测，AutoDL 西B区，CPU 16核）

### 结果 1：Baseline（n=20，depth=8，seed=42，随机电路）
| 后端 | 时间(s) | 保真度(vs numpy) | 备注 |
|---|---|---|---|
| numpy 精确态矢量（参考） | 8.08 | — | 2^20≈105万维，指数级 |
| qibotn 稠密张量网络（quimb） | 11.31 | 1.000000 | Baseline |
| qibotn MPS | 6.07 | 1.000000 | 低纠缠时更优 |

### 结果 2：规模化验证（n=24，depth=6，seed=42，随机电路）
| 后端 | 时间(s) | 相对 numpy 加速 | 保真度 |
|---|---|---|---|
| numpy 精确态矢量（参考） | 134.45 | 1× | — |
| qibotn 稠密张量网络 | 2.93 | **45×** | 1.000000 |
| qibotn MPS | 1.17 | **115×** | 1.000000 |

**分析**：精确态矢量随比特数指数增长（20→24 比特耗时 8.08→134.45s，约 16.6×，与 2^4=16 倍理论一致）；张量网络通过收缩顺序避免全态矢量物化，在 24 比特时显著占优，验证了可扩展性优势。MPS 模式进一步利用电路结构压缩中间张量，速度最快且保真度仍为 1.0。

## 优化与结论
- **已完成**：Baseline 稠密张量网络正确性校验（保真度 1.0）；MPS 模式对比；24 比特规模化验证（张量网络相对精确模拟加速 45×~115×）。
- **可选后续扩展（本次未做）**：MPS 截断误差-保真度权衡分析；收缩顺序/优化器参数影响；cuQuantum GPU 后端加速。
