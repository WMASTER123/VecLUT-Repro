"""Serial model runner. Trace and uninstrumented performance never run concurrently."""
import argparse, csv, hashlib, json, os, random, re, subprocess, threading
from pathlib import Path
from run_p2 import snapshot
from model_registry import MODELS

def records(path): return [json.loads(line) for line in path.read_text().splitlines()]

def main():
    p=argparse.ArgumentParser();p.add_argument('normal',type=Path);p.add_argument('profile',type=Path)
    p.add_argument('model',type=Path);p.add_argument('output',type=Path);p.add_argument('--quick',action='store_true')
    p.add_argument('--model-key',choices=MODELS,default='falcon3-1b-i2v4')
    a=p.parse_args();places=os.environ.get('OMP_PLACES','')
    if not re.fullmatch(r'\{\d+\}(,\{\d+\}){3,}',places): p.error('Use four explicit OMP_PLACES')
    cpus=list(map(int,re.findall(r'\d+',places)))
    if len(set(cpus))!=len(cpus) or not set(cpus)<=os.sched_getaffinity(0): p.error('Unavailable CPU place')
    a.output.mkdir(parents=True,exist_ok=False)
    stop=threading.Event()
    def monitor():
        with (a.output/'monitor.jsonl').open('w') as f:
            while not stop.is_set():
                f.write(json.dumps(snapshot())+'\n');f.flush();stop.wait(1)
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    commands=[];samples=[];setups=[]
    def run(label,binary,mode,P,G,B,t,repeats):
        cmd=[str(binary),str(a.model),mode,str(P),str(G),str(B),str(t),str(repeats)]
        commands.append(dict(label=label,argv=cmd))
        with (a.output/'commands.jsonl').open('a') as f:f.write(json.dumps(commands[-1])+'\n')
        with (a.output/(label+'.jsonl')).open('w') as out,(a.output/(label+'.stderr.log')).open('w') as err:
            proc=subprocess.run(cmd,stdout=out,stderr=err,timeout=1200)
        if proc.returncode: raise RuntimeError(f'{label} failed: {proc.returncode}; logs preserved')
        rows=records(a.output/(label+'.jsonl'));setup=rows[0]
        rs=[r for r in rows if r['record']=='sample']
        if len(rs)!=repeats or any(not r['finite_logits'] for r in rs):raise RuntimeError('Incomplete/invalid measurement')
        if mode=='decode' and any(r['decode_steps']!=G or r['decoded_tokens']!=G*B for r in rs):raise RuntimeError('Wrong decode denominator')
        spec=MODELS[a.model_key];count=spec['tensor_count']
        if setup['tensor_types'].get(spec['tensor_type'])!=count:raise RuntimeError('Unexpected pinned model tensor inventory')
        if setup['profile']:
            for r in rs:
                if r['prefill_i2v4_worker_calls']!=count*t or r['decode_i2v4_worker_calls']!=count*t*r['decode_steps']:
                    raise RuntimeError('Unexpected I2_V_4 calls: investigate graph execution')
        print(label+' passed',flush=True)
        return setup,rs
    try:
        trace=[]
        for B in [1,4]:
            outputs=[]
            for name,binary in [('normal',a.normal),('profile',a.profile)]:
                setup,rs=run(f'smoke-{name}-B{B}',binary,'smoke',32,48,B,4,1)
                if not rs[0]['output_token_ids'][0]:raise RuntimeError('Empty smoke generation')
                outputs.append(rs[0]['output_token_ids']);trace.append(dict(build=name,B=B,setup=setup,sample=rs[0]))
            if outputs[0]!=outputs[1]:raise RuntimeError('Normal/profile greedy output mismatch')
            if any(ids!=outputs[0][0] for ids in outputs[0]):raise RuntimeError('Shared-prompt streams differ')
            if B==1: single_output=outputs[0][0]
            elif outputs[0][0]!=single_output:raise RuntimeError('Single/parallel smoke output mismatch')
        (a.output/'path-verification.json').write_text(json.dumps(dict(passed=True,normal_profile_tokens_equal=True,records=trace),indent=2)+'\n')
        cases=[('prefill',n,0,1,t) for n in [32,128,256,512] for t in [1,2,4]]
        cases += [('decode',128,32,1,t) for t in [1,2,4]]
        cases += [('decode',128,32,b,4) for b in [4,8,16]]
        if a.quick: cases=[('prefill',32,0,1,4),('decode',128,8,1,4),('decode',128,8,4,4)]
        random.Random(20261117).shuffle(cases)
        for i,(mode,P,G,B,t) in enumerate(cases):
            label=f'{i:02d}-{mode}-P{P}-G{G}-B{B}-T{t}'
            setup,rs=run(label,a.normal,mode,P,G,B,t,5)
            setups.append(dict(case=label,**setup))
            for r in rs:
                samples.append(dict(case=label,mode=mode,P=P,G=G,B=B,threads=t,**{k:v for k,v in r.items() if k not in ('record','output_text','output_token_ids')}))
        with (a.output/'raw.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(samples[0]));w.writeheader();w.writerows(samples)
        (a.output/'setups.json').write_text(json.dumps(setups,indent=2)+'\n')
        manifest=dict(model_key=a.model_key,suite='quick' if a.quick else 'full',cases=cases,repeats=5,seed=20261117,
                      normal_sha256=hashlib.sha256(a.normal.read_bytes()).hexdigest(),profile_sha256=hashlib.sha256(a.profile.read_bytes()).hexdigest(),
                      env={k:os.environ.get(k) for k in ['OMP_WAIT_POLICY','OMP_DYNAMIC','OMP_PROC_BIND','OMP_PLACES']},
                      timing='model-forward prefill; autoregressive decode loop includes greedy finite-logit scan and host batch bookkeeping',
                      shared_prompt=True,ignore_eog_in_performance=True)
        (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        (a.output/'complete.json').write_text(json.dumps(dict(passed=True,cases=len(cases),samples=len(samples)))+'\n')
    finally:
        stop.set();thread.join()

if __name__=='__main__':main()
