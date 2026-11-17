"""Serial performance driver. Uses stdlib; plotting is a separate optional step."""
import argparse, csv, hashlib, json, os, random, re, subprocess, threading, time
from pathlib import Path

SHAPES = [('falcon_square',2048,2048),('falcon_up',8192,2048),('falcon_down',2048,8192),
          ('bitnet_square',3200,3200),('bitnet_up',8640,3200),('bitnet_down',3200,8640)]
NS=[1,8,16,31,32,33,63,64,65,128,256,512]
def snapshot():
    mem={}; vm={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        k,v=line.split(':',1)
        if k in ('MemAvailable','SwapTotal','SwapFree'): mem[k]=int(v.split()[0])
    for line in Path('/proc/vmstat').read_text().splitlines():
        k,v=line.split()
        if k in ('pswpin','pswpout'): vm[k]=int(v)
    cpu=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
    return dict(unix_s=time.time(),**mem,**vm,cpu_ticks=cpu,load1=float(Path('/proc/loadavg').read_text().split()[0]))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('binary',type=Path); p.add_argument('output',type=Path)
    p.add_argument('--suite',choices=['full','quick','profile','confirm'],default='full')
    p.add_argument('--repeats',type=int,default=5); p.add_argument('--target-ms',type=float,default=100)
    a=p.parse_args()
    places=os.environ.get('OMP_PLACES','')
    if not re.fullmatch(r'\{\d+\}(,\{\d+\}){3,}',places):
        p.error('OMP_PLACES must list at least four explicit virtual CPUs, e.g. {0},{2},{4},{6}')
    cpus=list(map(int,re.findall(r'\d+',places)))
    if len(set(cpus))!=len(cpus) or not set(cpus)<=os.sched_getaffinity(0):
        p.error('OMP_PLACES includes duplicate or unavailable virtual CPUs; use P2_OMP_PLACES override')
    a.output.mkdir(parents=True,exist_ok=False)
    shapes=SHAPES; ns=NS
    if a.suite in ('quick','profile'): shapes=[SHAPES[0],SHAPES[3]]; ns=[1,32,33,128]
    if a.suite=='confirm': shapes=[SHAPES[0],SHAPES[3]]; ns=[1,16,31,63,64,512]
    cases=[(name,m,k,n) for name,m,k in shapes for n in ns]
    if a.suite=='profile': cases += [('falcon_up',8192,2048,128),('bitnet_down',3200,8640,128)]
    random.Random(20261117).shuffle(cases)
    manifest=dict(suite=a.suite,repeats=a.repeats,target_ms=a.target_ms,cases=cases,
                  seed=20261117,inputs='synthetic ternary weights and deterministic INT8-representable activations',
                  binary_sha256=hashlib.sha256(a.binary.read_bytes()).hexdigest(),
                  env={k:os.environ.get(k) for k in ['OMP_WAIT_POLICY','OMP_DYNAMIC','OMP_PROC_BIND','OMP_PLACES']},
                  allowed_virtual_cpus=sorted(os.sched_getaffinity(0)),
                  model_download=False,model_hash=None)
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    stop=threading.Event()
    def monitor():
        with (a.output/'monitor.jsonl').open('w') as f:
            while not stop.is_set():
                f.write(json.dumps(snapshot())+'\n'); f.flush(); stop.wait(1)
    thread=threading.Thread(target=monitor,daemon=True); thread.start()
    all_rows=[]
    try:
        with (a.output/'commands.jsonl').open('w') as commands:
            for i,(name,m,k,n) in enumerate(cases):
                cmd=[str(a.binary),str(m),str(k),str(n),str(a.repeats),str(a.target_ms)]
                commands.write(json.dumps(cmd)+'\n'); commands.flush()
                prefix=f'{i:03d}-{name}-N{n}'
                with (a.output/(prefix+'.csv')).open('w') as out, (a.output/(prefix+'.stderr.log')).open('w') as err:
                    r=subprocess.run(cmd,stdout=out,stderr=err,timeout=240)
                if r.returncode: raise RuntimeError(f'{prefix} failed with {r.returncode}')
                rows=list(csv.DictReader((a.output/(prefix+'.csv')).open()))
                if len(rows)!=a.repeats*4: raise RuntimeError('unexpected number of measurements')
                for row in rows: row['shape']=name; row['case_order']=i
                all_rows+=rows
                print(f'[{i+1}/{len(cases)}] {name} M={m} K={k} N={n} done',flush=True)
    finally:
        stop.set(); thread.join()
    with (a.output/'raw.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(all_rows[0])); w.writeheader(); w.writerows(all_rows)
    (a.output/'complete.json').write_text(json.dumps(dict(cases=len(cases),samples=len(all_rows),passed=True))+'\n')
if __name__=='__main__': main()
