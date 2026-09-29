"""Audit every recorded run and emit reproducible summary tables."""
import csv
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
reference_checks=json.loads((ROOT/'results/reference_checks.json').read_text())
assert all(c['fft_check']['pass'] for c in reference_checks['checks'])
assert reference_checks['negative_control']['pass'] is False
groups=defaultdict(list)
rows=[]
all_checks=[]
failures=[]
hashes=defaultdict(set)
manifest=[json.loads(s) for s in (ROOT/'results/manifest.jsonl').read_text().splitlines() if s.strip()]
ids=[m['id'] for m in manifest]
assert len(ids)==len(set(ids)), 'Duplicate run IDs: use a fresh results directory.'
for m in manifest:
    if m['status']!='success':
        failures.append(m);continue
    path=ROOT/'results'/f"{m['id']}.json"
    d=json.loads(path.read_text())
    assert d['backend_class']=='qibotn.backends.quimb.QuimbBackend'
    assert d['cuda_visible_devices']==''
    for r in d['rows']:
        assert r['validation']['pass'], (m['id'],r)
        assert r['dtype']=='complex128'
        assert r['state_bytes']==16*2**r['qubits']
        assert r['validation']['relative_l2_phase_aligned'] <= 1e-10
        hashes[(r['qubits'],r['seed'])].add(r['qasm_sha256'])
        all_checks.append(r['validation']['relative_l2_phase_aligned'])
        if m['id'].startswith('kernel_') and r['qubits']!=6:
            flat={k:v for k,v in r.items() if k not in ['validation','stages']}
            flat.update({'run_id':m['id'],'command':m['command'],'process_wall_s':m['process_wall_s'],
                         'error_l2':r['validation']['relative_l2_phase_aligned'],'norm':r['validation']['norm'],
                         'fidelity':r['validation']['fidelity']})
            rows.append(flat)
            groups[(r['qubits'],r['threads'],r['optimizer'])].append(flat)
assert all(len(v)==1 for v in hashes.values()), 'Circuit definition changed between variants.'
for row in rows:
    d=json.loads((ROOT/'results'/f"{row['run_id']}.json").read_text())
    for pool in d['threadpools']:
        assert pool['num_threads']==row['threads'], (row['run_id'],pool)

summary=[]
for (n,th,opt),rr in sorted(groups.items()):
    vals=[r['execute_s'] for r in rr]
    summary.append({'qubits':n,'threads':th,'optimizer':opt,'repeats':len(vals),
                    'median_s':statistics.median(vals),'min_s':min(vals),'max_s':max(vals),
                    'stdev_s':statistics.stdev(vals) if len(vals)>1 else 0,
                    'max_error_l2':max(r['error_l2'] for r in rr),
                    'maxrss_mib':max(r['maxrss_mib'] for r in rr)})
for s in summary:
    base=next(x for x in summary if x['qubits']==s['qubits'] and x['threads']==16 and x['optimizer']=='native')
    s['speedup_vs_native16']=base['median_s']/s['median_s']
for filename,data in [('results.csv',rows),('summary.csv',summary)]:
    with (ROOT/filename).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
batch=json.loads((ROOT/'results/batch_summary.json').read_text())
assert len(batch)==6 and all(r['status']=='success' for r in batch)
assert all(r['qubits']==[8,10,12,14] for r in batch)
assert all(run_id in ids for r in batch for run_id in r['run_ids'])
batch_stats={}
for mode in ['fresh','resident']:
    vals=[r['wall_s'] for r in batch if r['mode']==mode and r['status']=='success']
    batch_stats[mode]={'repeats':len(vals),'median_s':statistics.median(vals),'min_s':min(vals),'max_s':max(vals)}
batch_stats['speedup']=batch_stats['fresh']['median_s']/batch_stats['resident']['median_s']
audit={'recorded_processes':len(manifest),'failed_processes':failures,'validated_states':len(all_checks),
       'max_relative_l2':max(all_checks),'unique_qasm_per_input':True,'thread_counts_verified':True,
       'kernel_rows':len(rows),'groups':summary,'batch':batch_stats,
       'expected_kernel_groups':15,'expected_repeats':5,
       'complete':len(summary)==15 and all(s['repeats']==5 for s in summary) and not failures
                  and len(manifest)==92 and len(all_checks)==178
                  and all(batch_stats[m]['repeats']==3 for m in ['fresh','resident'])}
(ROOT/'audit.json').write_text(json.dumps(audit,indent=2))
print(json.dumps(audit,indent=2))
