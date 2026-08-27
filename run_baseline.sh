#!/usr/bin/env bash
# 运行 QiboTN Baseline 并保存日志
# 用法:
#   bash run_baseline.sh                  # n=20, depth=8
#   bash run_baseline.sh 24 10            # n=24, depth=10
#   bash run_baseline.sh 20 8 --mps       # 额外跑 MPS 模式
set -euo pipefail

cd "$(dirname "$0")"
source "$HOME/qibotn-venv/bin/activate" 2>/dev/null || source qibotn-venv/bin/activate 2>/dev/null || {
  echo "[错误] 没找到 qibotn-venv，请先运行: bash setup_qibotn.sh"
  exit 1
}
mkdir -p logs

N="${1:-20}"
D="${2:-8}"
if [ $# -gt 2 ]; then
  shift 2
  EXTRA="$*"
else
  EXTRA=""
fi

echo "================ QiboTN Baseline ================"
echo "时间: $(date)"
echo "机器: $(hostname) | 核数: $(nproc) | 内存: $(free -h | awk '/^Mem:/{print $2}')"
echo "配置: n=$N, depth=$D ${EXTRA:+| 附加参数: $EXTRA}"
echo "Python: $(python --version 2>&1)"
echo "----------------------------------------------"

python baseline_qibotn.py --n "$N" --depth "$D" $EXTRA 2>&1 | tee "logs/baseline_n${N}_d${D}.log"

echo "----------------------------------------------"
echo "完成。查看: logs/baseline_n${N}_d${D}.log 和 .json"
