"""Run frozen graph gate and conditional paired model validation."""
from pathlib import Path
import json,os,subprocess,sys
from datetime import datetime
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
run=root/'results'/('lanes-'+datetime.now().strftime('%Y%m%d-%H%M%S'));run.mkdir(parents=True,exist_ok=False)
(root/'results/latest-lanes.txt').write_text(str(run)+'\n')
(run/'source-sha.txt').write_text(subprocess.check_output(['git','-C',str(here.parent),'rev-parse','HEAD'],text=True))
(run/'source.patch').write_bytes(subprocess.check_output(['git','-C',str(here.parent),'diff','--binary']))
os.environ.update(TMPDIR=str(root/'tmp'),XDG_CACHE_HOME=str(root/'cache'),PYTHONPYCACHEPREFIX=str(root/'cache/pycache'))
def execute(script,out,*args):
 with (run/(out+'.log')).open('w') as f:subprocess.run([sys.executable,str(here/script),str(root),str(run/out),*map(str,args)],stdout=f,stderr=subprocess.STDOUT,check=True)
execute('screen_valid_lanes.py','screen')
gate=json.loads((run/'screen/gate.json').read_text())
if not gate['proceed_to_models']:
 (run/'decision.json').write_text(json.dumps(dict(accepted=False,stage='screen',gate=gate),indent=2))
 print('STOP: graph gate failed; remove valid-lane implementation, retain evidence.');sys.exit(0)
plan=[]
for m in ('falcon3-1b-i2v4','bitnet-3b-i2v4'):
 for t in (1,4):
  for p in (16,33,47,65,32,128):
   plan.append(dict(model=m,P=p,threads=t,cpus=[2] if t==1 else [0,2,4,6],samples=6,variants=['deferred','valid'],role='guard' if p in (32,128) else 'target'))
  plan.append(dict(model=m,P=32,G=8,mode='decode',threads=t,cpus=[2] if t==1 else [0,2,4,6],samples=6,variants=['deferred','valid'],role='target'))
path=run/'model-plan.json';path.write_text(json.dumps(plan,indent=2));execute('paired_prefill.py','models',path)
initial=json.loads((run/'models/summary.json').read_text());noisy=[dict(s['case'],samples=10) for s in initial if max(v['cv'] for v in s['values'].values())>0.10]
if noisy:
 path=run/'repeat-plan.json';path.write_text(json.dumps(noisy,indent=2));execute('paired_prefill.py','repeat',path)
def key(s):
 c=s['case'];return c['model'],c['P'],c['threads'],c.get('mode','prefill')
extra=json.loads((run/'repeat/summary.json').read_text()) if noisy else [];rep={key(s):s for s in extra};selected=[rep.get(key(s),s) for s in initial]
good=sum(s['case']['role']=='target' and s['speedup']>=1.10 for s in selected)
bad=[key(s) for s in selected if s['speedup']<1/(1.03 if s['case']['role']=='guard' else 1.05)]
noise=[key(s) for s in selected if max(v['cv'] for v in s['values'].values())>0.10]
result=dict(accepted=good>10 and not bad and not noise,stage='models',target_good=good,regressions=bad,unresolved_noise=noise,selected=selected)
(run/'decision.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
