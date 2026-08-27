#!/usr/bin/env python3
"""QiboTN Baseline 脚本（已在 Linux 沙箱验证，正确性校验通过）

模拟随机量子电路，对比不同后端并验证正确性：
  1) numpy 精确态矢量模拟 (qibo 默认后端)  —— 参考标准
  2) qibotn 稠密张量网络 (quimb 后端)       —— 本题 Baseline
  3) (可选) qibotn MPS 模式                  —— 备选优化方向

用法:
  python baseline_qibotn.py --n 20 --depth 8 [--mps] [--seed 42]

输出:
  logs/baseline_n{...}_d{...}.json  结构化结果
  logs/baseline_n{...}_d{...}.log   终端日志（由 run_baseline.sh 生成）
"""
import argparse
import json
import os
import time

import numpy as np
from qibo import Circuit, gates, set_backend


def random_circuit(n, depth, seed=42):
    rng = np.random.default_rng(seed)
    c = Circuit(n)
    for _ in range(depth):
        for q in range(n):
            g = rng.choice([gates.X, gates.Y, gates.Z, gates.H, gates.S, gates.T])
            c.add(g(q))
        for q in range(n - 1):
            c.add(gates.CNOT(q, q + 1))
    return c


def timed(fn):
    t0 = time.perf_counter()
    out = fn()
    return time.perf_counter() - t0, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20, help="qubit 数")
    ap.add_argument("--depth", type=int, default=8, help="电路深度")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--mps", action="store_true", help="额外跑 MPS 模式")
    args = ap.parse_args()
    n, depth, seed = args.n, args.depth, args.seed

    c = random_circuit(n, depth, seed)
    log = {"n": n, "depth": depth, "seed": seed,
           "backend": "qibotn/quimb", "platform": "qutensornet"}

    # ---- 参考：numpy 精确态矢量（n 太大时跳过，改用范数校验）----
    ref = None
    if n <= 24:
        set_backend("numpy")
        t, res = timed(lambda: np.asarray(c().state()))
        ref = res
        log["numpy"] = {"time_s": round(t, 4), "norm": float(np.linalg.norm(ref))}
        print(f"[numpy]  n={n} depth={depth} time={t:.4f}s norm={np.linalg.norm(ref):.6f}")
    else:
        print(f"[numpy]  跳过参考（n={n} 态矢量过大），改用范数校验")

    settings = {"MPI_enabled": False, "MPS_enabled": False,
                "NCCL_enabled": False, "expectation_enabled": False}

    # ---- 预热 quimb 后端（排除一次性初始化开销）----
    set_backend("qibotn", platform="qutensornet", runcard=settings)
    cw = Circuit(4)
    for i in range(4):
        cw.add(gates.H(i))
    cw()
    print("(warmup 完成，后端已初始化)")

    # ---- qibotn 稠密张量网络：本题 Baseline ----
    t, s_tn = timed(lambda: np.asarray(c().state()))
    log["dense_tn"] = {"time_s": round(t, 4), "norm": float(np.linalg.norm(s_tn))}
    print(f"[qibotn] n={n} depth={depth} time={t:.4f}s norm={np.linalg.norm(s_tn):.6f}")

    # ---- 正确性校验 ----
    if ref is not None:
        fid = abs(np.vdot(ref, s_tn)) ** 2
        log["fidelity"] = float(fid)
        passed = fid > 0.9999
    else:
        log["fidelity"] = "skipped"
        passed = abs(np.linalg.norm(s_tn) - 1.0) < 1e-6
    print(f"[check] fidelity vs numpy = {log.get('fidelity')}  ->  {'PASSED' if passed else 'FAILED'}")

    # ---- MPS 模式（可选优化方向）----
    if args.mps:
        settings_mps = {"MPI_enabled": False, "MPS_enabled": True,
                        "NCCL_enabled": False, "expectation_enabled": False}
        set_backend("qibotn", platform="qutensornet", runcard=settings_mps)
        cw()
        t_m, s_mps = timed(lambda: np.asarray(c().state()))
        log["mps"] = {"time_s": round(t_m, 4)}
        print(f"[qibotn MPS] n={n} depth={depth} time={t_m:.4f}s")
        if ref is not None:
            fid_m = abs(np.vdot(ref, s_mps)) ** 2
            log["mps"]["fidelity"] = float(fid_m)
            print(f"[check] MPS fidelity = {fid_m:.6f}")

    log["passed"] = bool(passed)
    os.makedirs("logs", exist_ok=True)
    out = f"logs/baseline_n{n}_d{depth}.json"
    with open(out, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
    print(f"[OK] 结果已保存: {out}")
    print("PASSED" if passed else "FAILED")


if __name__ == "__main__":
    main()
