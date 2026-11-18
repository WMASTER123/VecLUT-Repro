"""Frozen short/tail graph screen against the unchanged deferred-layout baseline."""
import csv,json,os,statistics,subprocess,sys
from pathlib import Path
from run_p6 import memory
root,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
variants=['deferred','valid'];rows=[]
shapes=[(2048,2048),(8192,2048),(2048,8192),(3200,3200),(8640,3200),(3200,8640)]
cases=[(m,k,n,t) for m,k in shapes for n in (1,2,4,8,16,31,32,33,47,63,64,65,96,128) for t in (1,4)]
(out/'manifest.json').write_text(json.dumps(dict(cases=cases,variants=variants,batches=2,repeats=5,target_ms=50),indent=2))
def measure(ci,batch,v,target=50):
 m,k,n,t=cases[ci];cpus=[2] if t==1 else [0,2,4,6]
 env=os.environ.copy()
 for name in ('GOMP_CPU_AFFINITY','KMP_AFFINITY'):env.pop(name,None)
 env.update(OMP_NUM_THREADS=str(t),OMP_WAIT_POLICY='PASSIVE',OMP_DYNAMIC='FALSE',OMP_PROC_BIND='CLOSE',OMP_PLACES=','.join('{'+str(c)+'}' for c in cpus))
 label=f'b{batch}-c{ci}-{v}'
 cmd=['taskset','-c',','.join(map(str,cpus)),str(root/'builds'/f'p6-{v}'/'bin/bench-p2'),str(m),str(k),str(n),'5',str(target),f'graph{t}']
 before=memory()
 with (out/(label+'.csv')).open('w') as f,(out/(label+'.log')).open('w') as err:subprocess.run(cmd,env=env,stdout=f,stderr=err,check=True)
 after=memory();(out/(label+'-resources.json')).write_text(json.dumps(dict(command=cmd,before=before,after=after)))
 if any(before[x]!=after[x] for x in ('pswpin','pswpout')):raise RuntimeError('Swap activity')
 data=list(csv.DictReader((out/(label+'.csv')).open()))
 assert len(data)==5 and all(not int(x['profile']) and not int(x['major_faults']) for x in data)
 assert all(int(x[key]) in cpus for x in data for key in ('main_cpu_before','main_cpu_after'))
 rows.extend(dict(case_id=ci,batch=batch,variant=v,**x) for x in data)
for batch in range(2):
 for ci in (range(len(cases)) if batch==0 else reversed(range(len(cases)))):
  for v in (variants if (ci+batch)%2==0 else variants[::-1]):measure(ci,batch,v)
  print(f'batch {batch} case {ci}/{len(cases)} {cases[ci]} passed',flush=True)
def summarize(ci,batches):
 vals={v:[float(x['wall_us']) for x in rows if x['case_id']==ci and x['batch'] in batches and x['variant']==v] for v in variants}
 med={v:statistics.median(x) for v,x in vals.items()}
 return dict(speedup=med['deferred']/med['valid'],median_us=med,cv={v:statistics.stdev(x)/statistics.mean(x) for v,x in vals.items()})
summary=[];good=0;bad=[];guard_bad=[]
for ci,(m,k,n,t) in enumerate(cases):
 b=[summarize(ci,[i]) for i in (0,1)];r=dict(case_id=ci,M=m,K=k,N=n,threads=t,batches=b)
 if n%32:
  good+=all(x['speedup']>=1.10 for x in b)
  if all(x['speedup']<1/1.05 for x in b):bad.append(ci)
 else:
  if any(x['speedup']<1/1.03 for x in b):
   for batch in (2,3):
    for v in (variants if batch==2 else variants[::-1]):measure(ci,batch,v,150)
   r['guard_recheck']=summarize(ci,[2,3])
   if r['guard_recheck']['speedup']<1/1.03 or max(r['guard_recheck']['cv'].values())>0.10:guard_bad.append(ci)
 summary.append(r)
with (out/'samples.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
(out/'summary.json').write_text(json.dumps(summary,indent=2))
gate=dict(target_configs=120,guard_configs=48,target_both_batches_ge_10pct=good,target_consistent_regressions=bad,failed_guards=guard_bad,samples=len(rows),proceed_to_models=good>60 and not bad and not guard_bad)
(out/'gate.json').write_text(json.dumps(gate,indent=2));print(json.dumps(gate,indent=2))
