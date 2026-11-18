"""Repeat the frozen P6.4 model plan with unchanged, verified binaries."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from model_registry import MODELS

root = Path(sys.argv[1]).resolve()
old = root.parent/'deferred-transpose'
here = Path(__file__).resolve().parent
run = root/'results'/('recheck-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
run.mkdir(parents=True,exist_ok=False)
for folder in ('tmp','cache','builds'):(root/folder).mkdir(exist_ok=True)
for v in ('safe240','deferred'):
    p=root/'builds'/f'p6-{v}'
    if not p.exists():p.symlink_to(old/'builds'/f'p6-{v}',target_is_directory=True)
if not (root/'models').exists():(root/'models').symlink_to(old/'models',target_is_directory=True)
os.environ.update(TMPDIR=str(root/'tmp'),XDG_CACHE_HOME=str(root/'cache'),PYTHONPYCACHEPREFIX=str(root/'cache/pycache'))
expected=json.loads((old/'results/review-20261118/binary-hashes.json').read_text())
actual={}
for rel,digest in expected.items():
    if 'asan' in rel:continue
    actual[rel]=hashlib.sha256((old/rel).read_bytes()).hexdigest()
    if actual[rel]!=digest:raise RuntimeError(f'Existing binary changed: {rel}')
for key in ('falcon3-1b-i2v4','bitnet-3b-i2v4'):
    p=root/'models'/key/MODELS[key]['file']
    with p.open('rb') as f:actual[key]=hashlib.file_digest(f,'sha256').hexdigest()
    if actual[key]!=MODELS[key]['sha256']:raise RuntimeError('Model changed')
(run/'hashes.json').write_text(json.dumps(actual,indent=2))
plan=json.loads((old/'results/experiment-20261118-090744/model-plan.json').read_text())
(run/'plan.json').write_text(json.dumps(plan,indent=2))
(root/'results/latest-recheck.txt').write_text(str(run)+'\n')
def execute(out,planfile):
    with (run/(out+'.log')).open('w') as log:
        subprocess.run([sys.executable,str(here/'paired_prefill.py'),str(root),str(run/out),str(planfile)],stdout=log,stderr=subprocess.STDOUT,check=True)
execute('models',run/'plan.json')
initial=json.loads((run/'models/summary.json').read_text())
noisy=[dict(s['case'],samples=10) for s in initial if max(v['cv'] for v in s['values'].values())>0.10]
if noisy:
    (run/'repeat-plan.json').write_text(json.dumps(noisy,indent=2));execute('repeat',run/'repeat-plan.json')
def key(s):
    c=s['case'];return c['model'],c['P'],c['threads'],c.get('mode','prefill')
extra=json.loads((run/'repeat/summary.json').read_text()) if noisy else []
rep={key(s):s for s in extra};selected=[rep.get(key(s),s) for s in initial]
good=sum(s['case']['role']=='main' and s['speedup']>=1.05 for s in selected)
bad=[key(s) for s in selected if s['speedup']<1/1.05]
unresolved=[key(s) for s in selected if max(v['cv'] for v in s['values'].values())>0.10]
result=dict(main_good=good,regressions=bad,unresolved_noise=unresolved,passed=good>=6 and not bad and not unresolved,selected=selected)
(run/'decision.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
