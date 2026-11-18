"""Separate baseline-enhancement follow-up after the adaptive gate failed.

This never runs adaptive model performance or reverses the failed adaptive gate.
"""
import json
from pathlib import Path
import subprocess
import sys
root,run=map(Path,sys.argv[1:3]);here=Path(__file__).resolve().parent
plan=[dict(model=m,P=128,threads=t,cpus=[2] if t==1 else [0,2,4,6],samples=6,
           variants=['legacy128','safe240']) for m in ('falcon3-1b-i2v4','bitnet-3b-i2v4') for t in (1,4)]
path=run/'fixed-followup-plan.json';path.write_text(json.dumps(plan,indent=2))
with (run/'fixed-followup.log').open('w') as f:
    p=subprocess.Popen([sys.executable,str(here/'paired_prefill.py'),str(root),str(run/'fixed-followup'),str(path)],
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    for line in p.stdout:f.write(line);f.flush();print(line,end='',flush=True)
    if p.wait():raise RuntimeError('Fixed baseline follow-up failed')
summary=json.loads((run/'fixed-followup/summary.json').read_text())
noisy=[dict(s['case'],samples=10) for s in summary if max(v['cv'] for v in s['values'].values())>0.10]
if noisy:
    rp=run/'fixed-recheck-plan.json';rp.write_text(json.dumps(noisy,indent=2))
    with (run/'fixed-recheck.log').open('w') as f:
        subprocess.run([sys.executable,str(here/'paired_prefill.py'),str(root),str(run/'fixed-recheck'),str(rp)],stdout=f,stderr=subprocess.STDOUT,check=True)
