#!/usr/bin/env bash
# QiboTN 环境配置：建虚拟环境 + 安装 qibotn
# 适用: Ubuntu 22.04/24.04 租用服务器（有 root/sudo）
# 用法: bash setup_qibotn.sh 2>&1 | tee logs/setup_qibotn.log
set -euo pipefail

mkdir -p "$(dirname "$0")/logs"
cd "$(dirname "$0")"

echo "==================== [1/3] 安装 python3/venv ===================="
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip

echo "==================== [2/3] 创建虚拟环境 ===================="
cd "$HOME"
if [ ! -d qibotn-venv ]; then
  python3 -m venv qibotn-venv
fi
source qibotn-venv/bin/activate
pip install --upgrade pip -q

echo "==================== [3/3] 安装 qibotn ===================="
pip install qibotn

echo "==================== 验证 ===================="
python - <<'EOF'
import qibo, qibotn
print("qibo  版本:", qibo.__version__)
print("qibotn 导入: OK")
EOF

echo ""
echo "[完成] QiboTN 环境就绪。"
echo "       之后每次用: source ~/qibotn-venv/bin/activate"
echo "       然后: bash $(pwd)/run_baseline.sh"
