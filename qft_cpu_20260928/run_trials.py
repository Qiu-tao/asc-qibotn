"""Reproducible isolated CPU experiments, raw logs and timeout records."""
import argparse
import csv
import json
import os
import random
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
p=argparse.ArgumentParser()
p.add_argument('--repeats',type=int,default=5)
p.add_argument('--qubits',type=int,nargs='+',default=[8,12,16])
p.add_argument('--timeout',type=int,default=180)
p.add_argument('--batch-only',action='store_true')
a=p.parse_args()
Path('logs').mkdir(exist_ok=True);Path('results').mkdir(exist_ok=True)
manifest=[]
def run(label,ns,threads,optimizer,mode='worker'):
    cmd=[sys.executable,'benchmark.py','--mode',mode,'--qubits',*map(str,ns),
         '--threads',str(threads),'--optimizer',optimizer,'--output',f'results/{label}.json']
    entry={'id':label,'command':shlex.join(cmd),'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    t=time.perf_counter()
    with open(f'logs/{label}.log','w') as f:
        try:
            r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=a.timeout,
                             env={**os.environ,'CUDA_VISIBLE_DEVICES':'','PYTHONHASHSEED':'0'})
            entry['status']='success' if r.returncode==0 else 'failed'
            entry['returncode']=r.returncode
        except subprocess.TimeoutExpired:
            entry['status']='timeout'
    entry['process_wall_s']=time.perf_counter()-t
    manifest.append(entry)
    with open('results/manifest.jsonl','a') as f:f.write(json.dumps(entry)+'\n')
    print(json.dumps(entry),flush=True)
    return entry

if not a.batch_only:
    configs=[('native16',16,'native'),('native4',4,'native'),('native1',1,'native'),('greedy1',1,'greedy'),('autohq1',1,'auto-hq')]
    jobs=[(n,r,c) for n in a.qubits for r in range(a.repeats) for c in configs]
    random.Random(20260928).shuffle(jobs)
    failures={}
    for n,r,(label,th,opt) in jobs:
        key=(n,label)
        if failures.get(key,0)>=2:
            print('Skipping repeatedly failed configuration',key,flush=True)
            continue
        e=run(f'kernel_{label}_n{n}_r{r}',[6,n],th,opt)
        if e['status']!='success':failures[key]=failures.get(key,0)+1
    for opt in ['native','greedy']:
        run(f'profile_{opt}',[6,16],1,opt,'profile')

# Same fixed set of four circuits, same single CPU thread and native optimizer.
# End-to-end timing includes imports, execution, verification and JSON writes.
# Both modes verify four full states. Neither reuses calculated answers.
batch_records=[]
for r in range(3):
    modes=['fresh','resident'] if r%2==0 else ['resident','fresh']
    for mode in modes:
        t=time.perf_counter(); entries=[]
        if mode=='fresh':
            for n in [8,10,12,14]: entries.append(run(f'batch_fresh_r{r}_n{n}',[n],1,'native'))
        else:
            entries.append(run(f'batch_resident_r{r}',[8,10,12,14],1,'native'))
        row={'mode':mode,'repeat':r,'qubits':[8,10,12,14],
             'wall_s':time.perf_counter()-t,'status':'success' if all(e['status']=='success' for e in entries) else 'failed',
             'run_ids':[e['id'] for e in entries]}
        batch_records.append(row)
        Path('results/batch_summary.json').write_text(json.dumps(batch_records,indent=2))
print('COMPLETE',flush=True)
