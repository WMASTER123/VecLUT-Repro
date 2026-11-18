"""Full, unfiltered descriptive report from a completed motivation run."""
import csv
import json
from pathlib import Path
import statistics
import sys

run=Path(sys.argv[1]);out=run/(sys.argv[2] if len(sys.argv)>2 else 'analysis');out.mkdir(exist_ok=False)
screen=json.loads((run/'screen/summary.json').read_text())
lines=['# 安全累加实验：自动统计','', '加速比=对照中位耗时/候选中位耗时；保留全部配置与样本。','',
       '## 图级筛查（150ms目标，非最终模型结论）','','|M/K/N/线程|K240/K128 两批加速比|自适应/K240 两批加速比|','|---|---:|---:|']
for c in screen:
    a=[b['safe_vs_legacy'] for b in c['batches']];b=[b['adaptive_vs_safe'] for b in c['batches']]
    lines.append(f"|{c['M']}/{c['K']}/{c['N']}/{c['threads']}|{a[0]:.3f}/{a[1]:.3f}|{b[0]:.3f}/{b[1]:.3f}|")
models=[]
for stage in ('primary','extended','fixed-control','guards','fixed-followup'):
    if not (run/stage/'summary.json').exists():continue
    rows=[json.loads(s) for s in (run/stage/'samples.jsonl').read_text().splitlines()]
    summary=json.loads((run/stage/'summary.json').read_text())
    lines += ['',f'## {stage}','','|模型/P/线程/模式|对照ms|候选ms|加速比|块内比值范围|CV 对照/候选|','|---|---:|---:|---:|---:|---:|']
    for s in summary:
        c=s['case'];a,b=c['variants'];metric='decode_loop_ms' if c.get('mode')=='decode' else 'prefill_ms'
        rr=[r for r in rows if r['case_id']==s['case_id']];ratios=[]
        for block in sorted({r['block'] for r in rr}):
            med={v:statistics.median(r[metric] for r in rr if r['variant']==v and r['block']==block) for v in (a,b)}
            ratios.append(med[a]/med[b])
        item=dict(stage=stage,**s,block_speedups=ratios,samples=len(rr),hashes=len({r['last_logits_hash'] for r in rr}),
                  major_faults=sum(r['major_faults'] for r in rr),tokens_equal=len({json.dumps(r['output_token_ids']) for r in rr})==1)
        models.append(item);x=s['values'][a];y=s['values'][b]
        label=f"{c['model']}/P{c['P']}/{c.get('threads',1)}/{c.get('mode','prefill')}"
        lines.append(f"|{label}|{x['median_ms']:.2f}|{y['median_ms']:.2f}|{s['speedup']:.3f}|{min(ratios):.3f}–{max(ratios):.3f}|{x['cv']:.1%}/{y['cv']:.1%}|")
lines += ['','块内范围是观测值，不是置信区间。所有配置仍是同一会话，未验证跨平台或提示多样性。']
(out/'summary.md').write_text('\n'.join(lines)+'\n')
(out/'summary.json').write_text(json.dumps(dict(screen=screen,models=models,decision=json.loads((run/'decision.json').read_text())),indent=2))
print('Saved:',out)
