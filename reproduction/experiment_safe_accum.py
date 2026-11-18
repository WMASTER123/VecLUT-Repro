"""Serial motivation gate; existing model files only, never downloads."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from model_registry import MODELS

root,out=map(Path,sys.argv[1:3]);root=root.resolve();out.mkdir(parents=True,exist_ok=False)
here=Path(__file__).resolve().parent
def invoke(args,log):
    with log.open('w') as f:
        p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        for line in p.stdout: f.write(line);f.flush();print(line,end='',flush=True)
        if p.wait(): raise RuntimeError(f'Command failed; see {log}')

(out/'source-sha.txt').write_text(subprocess.check_output(['git','-C',str(here.parent),'rev-parse','HEAD'],text=True))
(out/'source.patch').write_text(subprocess.check_output(['git','-C',str(here.parent),'diff','--binary'],text=True))
verification={}
for v in ('legacy128','safe240','adaptive'):
    build=root/'builds'/f'p6-{v}'; cache=(build/'CMakeCache.txt').read_text()
    for flag in ('CMAKE_BUILD_TYPE:STRING=Release','VLUT_PROFILE:BOOL=OFF','VLUT_I2V4_SELECTIVE_WIDEN:BOOL=ON','VLUT_I2V4_BLOCKED_WIDEN:BOOL=OFF',
                 'TABLE_ENTRY_SIZE:STRING=32','WEIGHT_UNROLL_BLOCK:STRING=16','GGML_NATIVE:BOOL=ON','VLUT_AVX512:BOOL=OFF','GGML_OPENMP:BOOL=ON',
                 'LLAMA_SANITIZE_ADDRESS:BOOL=OFF','LLAMA_SANITIZE_UNDEFINED:BOOL=OFF'):
        if flag not in cache.splitlines(): raise RuntimeError(f'{v}: unexpected {flag}')
    if v!='legacy128' and f'VLUT_I2V4_ACCUM_POLICY:STRING={v}' not in cache.splitlines():raise RuntimeError('Wrong policy')
    shutil.copyfile(build/'CMakeCache.txt',out/f'{v}-CMakeCache.txt')
    files=[build/'bin/bench-p2',build/'bin/bench-p6r-model',build/'src/libllama.so',*list((build/'ggml/src').glob('*.so'))]
    verification[v]={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
for key in ('falcon3-1b-i2v4','bitnet-3b-i2v4'):
    spec=MODELS[key];path=root/'models'/key/spec['file']
    with path.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
    if digest!=spec['sha256']:raise RuntimeError('Model hash mismatch')
    verification[key]=dict(spec,path=str(path),verified=True)
(out/'verification.json').write_text(json.dumps(verification,indent=2))
invoke([sys.executable,str(here/'screen_safe_accum.py'),str(root),str(out/'screen')],out/'screen.log')
gate=json.loads((out/'screen/gate.json').read_text())
if not gate['proceed_to_models']:
    (out/'decision.json').write_text(json.dumps(dict(status='stopped_at_kernel_gate',gate=gate),indent=2));sys.exit(0)
def model_case(model,p,t,variants):
    return dict(model=model,P=p,threads=t,cpus=[2] if t==1 else [0,2,4,6],samples=6,variants=variants)
primary=[model_case(m,128,t,['safe240','adaptive']) for m in ('falcon3-1b-i2v4','bitnet-3b-i2v4') for t in (1,4)]
def measure(name,plan):
    pp=out/f'{name}-plan.json';pp.write_text(json.dumps(plan,indent=2))
    invoke([sys.executable,str(here/'paired_prefill.py'),str(root),str(out/name),str(pp)],out/f'{name}.log')
    return json.loads((out/name/'summary.json').read_text())
results=measure('primary',primary)
if not all(s['speedup']>1.05 for s in results):
    (out/'decision.json').write_text(json.dumps(dict(status='limited_primary_result_no_expansion',primary_speedups=[s['speedup'] for s in results]),indent=2));sys.exit(0)
extended=[model_case(m,p,t,['safe240','adaptive']) for m in ('falcon3-1b-i2v4','bitnet-3b-i2v4') for p in (32,256) for t in (1,4)]
measure('extended',extended)
# Attribution control: do not credit all gains over conservative K128 to adaptation.
measure('fixed-control',[model_case(m,128,t,['legacy128','safe240']) for m in ('falcon3-1b-i2v4','bitnet-3b-i2v4') for t in (1,4)])
# Guard short/partial input and decode, rather than only full prefill tiles.
guards=[model_case(m,33,1,['safe240','adaptive']) for m in ('falcon3-1b-i2v4','bitnet-3b-i2v4')]
guards += [dict(model_case(m,32,4,['safe240','adaptive']),mode='decode',G=8) for m in ('falcon3-1b-i2v4','bitnet-3b-i2v4')]
measure('guards',guards)
(out/'decision.json').write_text(json.dumps(dict(status='completed_all_planned_confirmations',default_changed=False,merge_to_stable=False),indent=2))
