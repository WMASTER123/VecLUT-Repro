"""Short fixed-CPU shape screen; results require whole-model confirmation.

Usage: screen_widen_shapes.py DATA_DIR OUTPUT_DIR [baseline candidate]
"""
import csv
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys


def main():
    root, out = map(Path, sys.argv[1:3])
    variants = sys.argv[3:5] or ["off", "on"]
    if len(variants) != 2: raise ValueError("two variants required")
    out.mkdir(parents=True, exist_ok=False)
    shapes = [(2048,2048),(8192,2048),(2048,8192),(3200,3200),(8640,3200),(3200,8640)]
    cases = [(m,k,n,t) for m,k in shapes for n in (1,16,32,33,128,256) for t in (1,4)]
    cases += [(m,3200,n,1) for m in (2560,3072,4096) for n in (32,128)]
    (out/"manifest.json").write_text(json.dumps(dict(cases=cases,variants=variants,
        target_ms=150,repeats=5,batches=2,scope="screening only; 150 ms target, not 1s confirmation"),indent=2))
    all_rows=[]
    for batch in range(2):
        ids=range(len(cases)) if batch==0 else reversed(range(len(cases)))
        for case_id in ids:
            m,k,n,t=cases[case_id]
            cpus=[0] if t==1 else [0,2,4,6]
            env=os.environ.copy()
            env.update(OMP_PLACES=",".join("{"+str(c)+"}" for c in cpus),
                       OMP_PROC_BIND="CLOSE",OMP_DYNAMIC="FALSE",OMP_WAIT_POLICY="PASSIVE",OMP_NUM_THREADS=str(t))
            for variant in (variants if batch==0 else variants[::-1]):
                label=f"b{batch}-c{case_id}-{variant}"
                args=["taskset","-c",",".join(map(str,cpus)),str(root/"builds"/f"p6-{variant}"/"bin/bench-p2"),
                      str(m),str(k),str(n),"5","150",f"graph{t}"]
                with (out/f"{label}.csv").open("w") as f,(out/f"{label}.log").open("w") as err:
                    subprocess.run(args,stdout=f,stderr=err,env=env,check=True)
                rows=list(csv.DictReader((out/f"{label}.csv").open()))
                if len(rows)!=5 or any(int(r["profile"]) or int(r["major_faults"]) for r in rows):
                    raise RuntimeError("invalid screen measurement")
                all_rows.extend(dict(case_id=case_id,batch=batch,variant=variant,**r) for r in rows)
            if case_id%6==0:print(f"shape screen batch {batch} case {case_id}/{len(cases)}",flush=True)
    with (out/"samples.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,all_rows[0].keys());w.writeheader();w.writerows(all_rows)
    summary=[]
    for i,(m,k,n,t) in enumerate(cases):
        batches=[]
        for batch in range(2):
            x={v:[float(r["wall_us"]) for r in all_rows if r["case_id"]==i and r["batch"]==batch and r["variant"]==v] for v in variants}
            med={v:statistics.median(rows) for v,rows in x.items()}
            batches.append(dict(median_us=med,speedup=med[variants[0]]/med[variants[1]],
                                cv={v:statistics.stdev(rows)/statistics.mean(rows) for v,rows in x.items()}))
        summary.append(dict(case_id=i,M=m,K=k,N=n,threads=t,rows_per_thread=m/t,batches=batches))
    (out/"summary.json").write_text(json.dumps(summary,indent=2))


if __name__=="__main__":main()
