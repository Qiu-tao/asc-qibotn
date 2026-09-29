#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -e results/manifest.jsonl ]; then
  echo 'Existing experiment records found. Copy source + lock file into a fresh directory first.' >&2
  exit 1
fi
export CUDA_VISIBLE_DEVICES=''
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
mkdir -p logs results
.venv/bin/python -m pip check > logs/pip_check.log
.venv/bin/python benchmark.py --mode environment --output results/environment.json > logs/environment.log 2>&1
.venv/bin/python benchmark.py --mode reference --qubits 6 8 10 12 14 16 --output results/reference_checks.json > logs/reference.log 2>&1
.venv/bin/python run_trials.py > logs/trials.log 2>&1
.venv/bin/python summarize.py > logs/audit.log 2>&1
echo 'Complete: see audit.json, results.csv, summary.csv, logs/ and results/.'
