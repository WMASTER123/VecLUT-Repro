"""Matched normal/profile diagnostics; worker sums are not elapsed latency."""
from pathlib import Path
import csv,json,os,statistics,subprocess,sys
from run_p6 import memory
root,out=map(Path,sys.argv[1:3]); rows=[]
for m,k in ((2048,2048),(3200,3200)):
 for n in (1,32,33,128):
  for t in (1,4):
   cpus=[2] if t==1 else [0,2,4,6]
   env=os.environ.copy();env.update(OMP_NUM_THREADS=str(t),OMP_WAIT_POLICY='PASSIVE',OMP_DYNAMIC='FALSE',OMP_PROC_BIND='CLOSE',OMP_PLACES=','.join('{'+str(c)+'}' for c in cpus))
   for v,mode in (('safe240','normal'),('deferred','normal'),('deferred','profile'),('safe240','profile')):
    build=root/'builds'/((f'p6-{v}') if mode=='normal' else f'profile-{v}')
    label=f'{m}-{n}-{t}-{v}-{mode}'
    cmd=['taskset','-c',','.join(map(str,cpus)),str(build/'bin/bench-p2'),str(m),str(k),str(n),'5','100',f'graph{t}']
    before=memory()
    with (out/(label+'.csv')).open('w') as f,(out/(label+'.log')).open('w') as err:subprocess.run(cmd,env=env,stdout=f,stderr=err,check=True)
    after=memory()
    (out/(label+'-resources.json')).write_text(json.dumps(dict(command=cmd,before=before,after=after)))
    if any(before[x]!=after[x] for x in ('pswpin','pswpout')):raise RuntimeError('Swap')
    data=list(csv.DictReader((out/(label+'.csv')).open()))
    assert len(data)==5 and all(int(x['profile'])==(mode=='profile') and not int(x['major_faults']) for x in data)
    rows.extend(dict(variant=v,diagnostic=mode,**x) for x in data)
   print(f'diagnostic {m}/{n}/{t} complete',flush=True)
with (out/'samples.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
summary=[]
phases=['alloc_init','build','lookup','widen','output','free','activation','clear']
for m in (2048,3200):
 for n in (1,32,33,128):
  for t in (1,4):
   for v in ('safe240','deferred'):
    selected=[x for x in rows if int(x['M'])==m and int(x['N'])==n and int(x['threads'])==t and x['variant']==v]
    p=[x for x in selected if x['diagnostic']=='profile'];normal=[x for x in selected if x['diagnostic']=='normal']
    med={k:statistics.median(float(x[k+'_worker_us']) for x in p) for k in phases};total=sum(med.values())
    summary.append(dict(M=m,N=n,threads=t,variant=v,worker_us=med,worker_percent={k:100*val/total for k,val in med.items()},normal_us=statistics.median(float(x['wall_us']) for x in normal),profile_us=statistics.median(float(x['wall_us']) for x in p),normal_cv=statistics.stdev(float(x['wall_us']) for x in normal)/statistics.mean(float(x['wall_us']) for x in normal),profile_cv=statistics.stdev(float(x['wall_us']) for x in p)/statistics.mean(float(x['wall_us']) for x in p)))
(out/'summary.json').write_text(json.dumps(summary,indent=2))
