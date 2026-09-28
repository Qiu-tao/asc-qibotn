"""CPU QiboTN benchmark. No final-answer cache; full complex128 state each time."""
import argparse
import hashlib
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path

BOOT = time.perf_counter()
p = argparse.ArgumentParser()
p.add_argument('--mode', choices=['reference', 'worker', 'environment', 'profile'], required=True)
p.add_argument('--qubits', type=int, nargs='+', default=[8, 10, 12, 14])
p.add_argument('--threads', type=int, default=1)
p.add_argument('--optimizer', default='native', choices=['native', 'greedy', 'auto-hq'])
p.add_argument('--seed', type=int, default=20260928)
p.add_argument('--output', default='results/worker.json')
p.add_argument('--save-state', action='store_true', help='Save full state after timed computation; excluded from execute_s.')
a = p.parse_args()
for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'NUMBA_NUM_THREADS', 'QUIMB_NUM_THREAD_WORKERS']:
    os.environ[key] = str(a.threads)
os.environ['CUDA_VISIBLE_DEVICES'] = ''

import numpy as np
import qibo
from qibo import gates
from qibo.models import Circuit, QFT
from qibo.backends import NumpyBackend
from threadpoolctl import threadpool_info, threadpool_limits

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
Path('references').mkdir(exist_ok=True)
Path('results').mkdir(exist_ok=True)
TOL = 1e-10

def circuits(n):
    rng = np.random.default_rng(a.seed + n)
    prep = Circuit(n)
    for i in range(n):
        prep.add(gates.RY(i, theta=float(rng.uniform(-np.pi, np.pi))))
        prep.add(gates.RZ(i, theta=float(rng.uniform(-np.pi, np.pi))))
    for i in range(n - 1):
        prep.add(gates.CNOT(i, i + 1))
    return prep, prep + QFT(n, with_swaps=True)

def digest(c):
    return hashlib.sha256(c.to_qasm().encode()).hexdigest()

def compare(got, ref):
    got, ref = np.asarray(got).reshape(-1), np.asarray(ref).reshape(-1)
    if got.shape != ref.shape:
        return {'pass': False, 'reason': 'shape mismatch'}
    overlap = np.vdot(ref, got)
    phase = overlap / abs(overlap) if abs(overlap) else 1.0
    norm = float(np.linalg.norm(got))
    err = float(np.linalg.norm(got / phase - ref) / np.linalg.norm(ref))
    fidelity = float(abs(overlap)**2 / (np.vdot(ref, ref).real * np.vdot(got, got).real))
    return {'pass': bool(np.isfinite(got).all() and err <= TOL and abs(norm - 1) <= TOL),
            'relative_l2_phase_aligned': err, 'max_abs_error': float(np.max(np.abs(got / phase - ref))),
            'norm': norm, 'fidelity': fidelity, 'tolerance': TOL}

def install_optimizer(name, profile=False):
    # Native baseline is unmodified QiboTN 0.0.3. Other variants preserve its
    # QASM conversion and DRC simplification; only the contraction optimizer changes.
    if name == 'native' and not profile:
        return None
    import qibotn.eval_qu as eq
    import quimb.tensor as qtn
    stages = {}
    def dense(qasm, initial_state, mps_opts, backend='numpy'):
        assert initial_state is None and mps_opts is None and backend == 'numpy'
        t = time.perf_counter()
        c = qtn.circuit.Circuit.from_openqasm2_str(qasm, psi0=None, gate_opts=None)
        stages['qasm_parse_build_s'] = time.perf_counter() - t
        t = time.perf_counter()
        tn = c.psi.full_simplify(seq='DRC')
        stages['simplify_s'] = time.perf_counter() - t
        t = time.perf_counter()
        out = tn.to_dense(backend='numpy') if name == 'native' else tn.to_dense(backend='numpy', optimize=name)
        stages['contract_including_path_s'] = time.perf_counter() - t
        return out
    eq.dense_vector_tn_qu = dense
    return stages

def get_tn():
    from qibotn.backends import MetaBackend
    return MetaBackend.load(platform='qutensornet', runcard={
        'MPI_enabled': False, 'NCCL_enabled': False,
        'MPS_enabled': False, 'expectation_enabled': False})

with threadpool_limits(limits=a.threads):
    if a.mode == 'environment':
        import importlib.metadata as md
        b = get_tn()
        env = {'python': sys.version, 'platform': platform.platform(), 'affinity': sorted(os.sched_getaffinity(0)),
               'packages': {n: md.version(n) for n in ['qibo','qibotn','quimb','numpy','scipy','cotengra','numba','threadpoolctl']},
               'backend_class': type(b).__module__ + '.' + type(b).__name__, 'threadpools': threadpool_info(),
               'cuda_visible_devices': os.environ['CUDA_VISIBLE_DEVICES']}
        for path in ['/sys/fs/cgroup/cpu.max','/sys/fs/cgroup/memory.max','/proc/cpuinfo']:
            if Path(path).exists(): env[path] = Path(path).read_text()
        Path(a.output).write_text(json.dumps(env, indent=2))
        print(json.dumps({k:v for k,v in env.items() if k != '/proc/cpuinfo'}))
    elif a.mode == 'reference':
        b = NumpyBackend()
        checks = []
        for n in a.qubits:
            prep, c = circuits(n)
            init = np.asarray(b.execute_circuit(prep).state())
            ref = np.asarray(b.execute_circuit(c).state())
            analytic = np.fft.ifft(init) * np.sqrt(2**n)
            check = compare(ref, analytic)
            if not check['pass']: raise RuntimeError(('QFT vs FFT failed',n,check))
            np.savez(f'references/qft_{n}_{a.seed}.npz', state=ref, qasm_sha256=digest(c))
            checks.append({'qubits': n, 'qasm_sha256':digest(c), 'gates':len(c.queue), 'fft_check':check})
        # A deliberately wrong state must fail the validator.
        wrong = ref.copy(); wrong[0] += 0.1; wrong /= np.linalg.norm(wrong)
        negative = compare(wrong, ref)
        if negative['pass']: raise RuntimeError('Validator accepted wrong result')
        result = {'reference_backend':'qibo.backends.NumpyBackend', 'independent_oracle':'sqrt(2**n)*numpy.fft.ifft(prepared_state)',
                  'checks':checks, 'negative_control':negative}
        Path(a.output).write_text(json.dumps(result,indent=2)); print(json.dumps(result))
    else:
        t = time.perf_counter(); b = get_tn(); stages = install_optimizer(a.optimizer, a.mode == 'profile')
        setup_s = time.perf_counter() - t
        rows=[]
        for n in a.qubits:
            t=time.perf_counter(); _, c=circuits(n); build_s=time.perf_counter()-t
            h=digest(c)
            with np.load(f'references/qft_{n}_{a.seed}.npz') as saved:
                ref=saved['state']; assert str(saved['qasm_sha256'])==h
            t=time.perf_counter(); ct=time.process_time()
            state=np.asarray(b.execute_circuit(c, return_array=True)).reshape(-1)
            cpu_s=time.process_time()-ct; elapsed=time.perf_counter()-t
            check=compare(state,ref)
            if a.save_state:
                np.save(Path(a.output).with_suffix(f'.n{n}.state.npy'), state)
            row={'workload':'prepared_QFT','qubits':n,'seed':a.seed,'gates':len(c.queue),
                 'threads':a.threads,'optimizer':a.optimizer,'qasm_sha256':h,'dtype':str(state.dtype),
                 'build_s':build_s,'execute_s':elapsed,'cpu_s':cpu_s,'state_bytes':state.nbytes,
                 'maxrss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                 'validation':check,'status':'success' if check['pass'] else 'incorrect'}
            if stages is not None: row['stages']=dict(stages)
            rows.append(row); print(json.dumps(row),flush=True)
        result={'rows':rows,'backend_class':type(b).__module__+'.'+type(b).__name__,
                'setup_s':setup_s,'program_s':time.perf_counter()-BOOT,'threadpools':threadpool_info(),
                'command':sys.argv,'cuda_visible_devices':os.environ['CUDA_VISIBLE_DEVICES']}
        Path(a.output).parent.mkdir(parents=True,exist_ok=True)
        Path(a.output).write_text(json.dumps(result,indent=2))
        if not all(r['validation']['pass'] for r in rows): sys.exit(2)
