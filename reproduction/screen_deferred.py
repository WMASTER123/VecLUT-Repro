"""Frozen two-layout screen; no model/shape-specific candidate dispatch."""
import csv
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
from run_p6 import memory

root, out = map(Path, sys.argv[1:3])
out.mkdir(parents=True, exist_ok=False)
variants = ['safe240', 'deferred']
shapes = [(2048,2048),(8192,2048),(2048,8192),(3200,3200),(8640,3200),(3200,8640)]
cases = [(m,k,n,t) for m,k in shapes for n in (32,128) for t in (1,4)]
(out/'manifest.json').write_text(json.dumps(dict(cases=cases, variants=variants, target_ms=150, repeats=5, batches=2), indent=2))
rows = []
for batch in range(2):
    for ci in (range(len(cases)) if batch == 0 else reversed(range(len(cases)))):
        m,k,n,t = cases[ci]
        cpus = [2] if t == 1 else [0,2,4,6]
        env = os.environ.copy()
        for key in ('GOMP_CPU_AFFINITY', 'KMP_AFFINITY'):
            env.pop(key, None)
        env.update(OMP_PROC_BIND='CLOSE', OMP_WAIT_POLICY='PASSIVE', OMP_DYNAMIC='FALSE',
                   OMP_NUM_THREADS=str(t), OMP_PLACES=','.join('{'+str(c)+'}' for c in cpus))
        for v in (variants if (batch+ci)%2 == 0 else variants[::-1]):
            label = f'b{batch}-c{ci}-{v}'
            command = ['taskset','-c',','.join(map(str,cpus)),str(root/'builds'/f'p6-{v}'/'bin/bench-p2'),str(m),str(k),str(n),'5','150',f'graph{t}']
            with (out/f'{label}.csv').open('w') as f, (out/f'{label}.log').open('w') as err:
                before = memory()
                subprocess.run(command, env=env, stdout=f, stderr=err, check=True)
                after = memory()
            (out/f'{label}-resources.json').write_text(json.dumps(dict(before=before,after=after,command=command)))
            if any(before[k] != after[k] for k in ('pswpin','pswpout')):
                raise RuntimeError('Swap activity')
            data = list(csv.DictReader((out/f'{label}.csv').open()))
            if len(data) != 5 or any(int(r['profile']) or int(r['major_faults']) for r in data):
                raise RuntimeError('Invalid sample')
            rows.extend(dict(case_id=ci,batch=batch,variant=v,**r) for r in data)
        print(f'batch {batch} case {ci}: {m}/{k}/{n}/{t} complete', flush=True)
with (out/'samples.csv').open('w', newline='') as f:
    w = csv.DictWriter(f, rows[0].keys()); w.writeheader(); w.writerows(rows)
summary = []
for ci,(m,k,n,t) in enumerate(cases):
    batches = []
    for batch in range(2):
        x = {v:[float(r['wall_us']) for r in rows if r['case_id']==ci and r['batch']==batch and r['variant']==v] for v in variants}
        med = {v:statistics.median(vals) for v,vals in x.items()}
        batches.append(dict(median_us=med, speedup=med['safe240']/med['deferred'],
                            cv={v:statistics.stdev(vals)/statistics.mean(vals) for v,vals in x.items()}))
    summary.append(dict(M=m,K=k,N=n,threads=t,batches=batches))
(out/'summary.json').write_text(json.dumps(summary,indent=2))
passed = sum(all(b['speedup']>1.05 for b in s['batches']) for s in summary)
regressed = sum(any(b['speedup']<1/1.05 for b in s['batches']) for s in summary)
(out/'gate.json').write_text(json.dumps(dict(configurations=24,samples=len(rows),both_batches_gt_5pct=passed,
    any_batch_regression_gt_5pct=regressed,proceed_to_models=passed>12 and regressed<=2),indent=2))
print((out/'gate.json').read_text())
