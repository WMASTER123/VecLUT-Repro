"""Evaluate the frozen gates; preserve initial data even when a recheck exists."""
import json
from pathlib import Path
import statistics
import sys

run = Path(sys.argv[1])
screen = json.loads((run/'screen/gate.json').read_text())
decision = dict(screen=screen, accepted=False)
lines = ['# P6.4 测量摘要', '', '对照与候选均为固定 K240；speedup=对照中位耗时/候选中位耗时。', '']
lines += [f"图筛查：{screen['both_batches_gt_5pct']}/24 两批均快5%以上；{screen['any_batch_regression_gt_5pct']}/24 至少一批慢5%以上。", '']
if (run/'models/summary.json').exists():
    initial = json.loads((run/'models/summary.json').read_text())
    rechecks = json.loads((run/'recheck/summary.json').read_text()) if (run/'recheck/summary.json').exists() else []
    def key(s):
        c = s['case']
        return c['model'],c['P'],c['threads'],c.get('mode','prefill'),c.get('G',0)
    replacement = {key(s):s for s in rechecks}
    selected = [replacement.get(key(s),s) for s in initial]
    main = [s for s in selected if s['case']['role']=='main']
    good = sum(s['speedup']>=1.05 for s in main)
    regress = [key(s) for s in selected if s['speedup']<1/1.05]
    noisy = [key(s) for s in selected if max(v['cv'] for v in s['values'].values())>0.10]
    accepted = screen['proceed_to_models'] and len(main)==8 and len(selected)==14 and good>=6 and not regress and not noisy
    decision.update(accepted=accepted,main_ge_5pct=good,regressions=regress,unresolved_noise=noisy,selected=selected)
    lines += ['|模型|模式|P|线程|对照ms|候选ms|加速比|CV 对照/候选|复测|', '|---|---|---:|---:|---:|---:|---:|---|---|']
    for s in selected:
        c=s['case']; a=s['values']['safe240']; b=s['values']['deferred']
        lines.append(f"|{c['model']}|{c.get('mode','prefill')}|{c['P']}|{c['threads']}|{a['median_ms']:.3f}|{b['median_ms']:.3f}|{s['speedup']:.4f}x|{a['cv']:.1%}/{b['cv']:.1%}|{'是' if key(s) in replacement else '否'}|")
    lines += ['',f'主配置≥5%改善：{good}/8；退化配置：{len(regress)}；复测后CV>10%：{len(noisy)}。']
    evidence=[]
    for d in ('models','recheck'):
        path=run/d/'samples.jsonl'
        if path.exists(): evidence += [json.loads(line) for line in path.read_text().splitlines()]
    decode=[s for s in evidence if s['case'].get('mode')=='decode']
    decision.update(model_samples=len(evidence),decode_samples=len(decode),
                    decode_tokens_nonempty=all(bool(s['output_token_ids']) and
                        all(bool(seq) for seq in s['output_token_ids']) for s in decode))
    if not decode or not decision['decode_tokens_nonempty']:
        decision['accepted']=False
        lines += ['', 'Decode证据缺失或token为空：拒绝验收。']
lines += ['', '决定：'+('保留独立候选；默认关闭，尚未跨日/跨机器验证。' if decision['accepted'] else '未达到预注册门槛；删除候选代码，不按成功形状调参。'), '']
(run/'decision.json').write_text(json.dumps(decision,indent=2))
(run/'MEASUREMENTS.md').write_text('\n'.join(lines))
print('\n'.join(lines))
