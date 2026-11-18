"""Screen, then (only if passed) paired model tests under the frozen protocol."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime
from model_registry import MODELS

root = Path(sys.argv[1]).resolve()
here = Path(__file__).resolve().parent
run = root/'results'/('experiment-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
run.mkdir(parents=True, exist_ok=False)
(root/'results/latest-experiment.txt').write_text(str(run)+'\n')
os.environ.update(TMPDIR=str(root/'tmp'),XDG_CACHE_HOME=str(root/'cache'),PYTHONPYCACHEPREFIX=str(root/'cache/pycache'))
(run/'source-sha.txt').write_text(subprocess.check_output(['git','-C',str(here.parent),'rev-parse','HEAD'],text=True))
(run/'source.patch').write_bytes(subprocess.check_output(['git','-C',str(here.parent),'diff','--binary']))

def execute(script, *args):
    with (run/(Path(script).stem+'-'+str(len(list(run.glob('*.log'))))+'.log')).open('w') as f:
        p = subprocess.Popen([sys.executable,str(here/script),*map(str,args)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        for line in p.stdout:
            f.write(line); f.flush(); print(line,end='',flush=True)
        if p.wait(): raise RuntimeError(f'{script} failed')

execute('screen_deferred.py', root, run/'screen')
gate = json.loads((run/'screen/gate.json').read_text())
if not gate['proceed_to_models']:
    print('STOP: screen failed; retire candidate, do not tune shapes.',flush=True)
    sys.exit(0)
models = ('falcon3-1b-i2v4','bitnet-3b-i2v4')
hashes = {}
for model in models:
    path = root/'models'/model/MODELS[model]['file']
    with path.open('rb') as f: hashes[model] = hashlib.file_digest(f,'sha256').hexdigest()
    if hashes[model] != MODELS[model]['sha256'] or path.stat().st_size != MODELS[model]['size_bytes']:
        raise RuntimeError(f'Pinned model verification failed: {model}')
(run/'models.sha256.json').write_text(json.dumps(hashes,indent=2))
plan = []
for model in models:
    for p in (32,128):
        for t in (1,4):
            plan.append(dict(model=model,P=p,threads=t,cpus=[2] if t==1 else [0,2,4,6],samples=6,variants=['safe240','deferred'],role='main'))
    plan.append(dict(model=model,P=33,threads=1,cpus=[2],samples=6,variants=['safe240','deferred'],role='tail'))
    for t in (1,4):
        plan.append(dict(model=model,P=32,G=8,mode='decode',threads=t,cpus=[2] if t==1 else [0,2,4,6],samples=6,variants=['safe240','deferred'],role='decode'))
path = run/'model-plan.json'; path.write_text(json.dumps(plan,indent=2))
execute('paired_prefill.py',root,run/'models',path)
summary = json.loads((run/'models/summary.json').read_text())
noisy = [dict(s['case'],samples=10) for s in summary if max(v['cv'] for v in s['values'].values())>0.10]
if noisy:
    path = run/'recheck-plan.json'; path.write_text(json.dumps(noisy,indent=2))
    execute('paired_prefill.py',root,run/'recheck',path)
print(f'Finished. Review original and recheck results before acceptance: {run}',flush=True)
