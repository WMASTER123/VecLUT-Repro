import csv,json,statistics as st,sys
from collections import defaultdict
from pathlib import Path
root=Path(sys.argv[1]);rows=list(csv.DictReader((root/'raw.csv').open()));groups=defaultdict(list)
for r in rows:groups[r['case']].append(r)
summary=[]
for case,g in groups.items():
    mode=g[0]['mode'];key='prefill_ms' if mode=='prefill' else 'decode_loop_ms'
    vals=[float(r[key]) for r in g];med=st.median(vals);q=st.quantiles(vals,n=4,method='inclusive')
    P,G,B,t=[int(g[0][x]) for x in ['P','G','B','threads']]
    summary.append(dict(case=case,mode=mode,P=P,G=G,B=B,threads=t,samples=len(g),median_ms=med,min_ms=min(vals),max_ms=max(vals),
                        iqr_ms=q[2]-q[0],cv=st.stdev(vals)/st.mean(vals),tokens_s=(P if mode=='prefill' else G*B)*1000/med,
                        per_sequence_tokens_s=(P if mode=='prefill' else G)*1000/med,
                        decode_model_median_ms=st.median(float(r['decode_model_ms']) for r in g),
                        peak_process_kib=max(int(r['peak_process_kib']) for r in g),major_faults=sum(int(r['major_faults']) for r in g)))
with (root/'summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
mon=[json.loads(line) for line in (root/'monitor.jsonl').read_text().splitlines()]
quality=dict(configurations=len(summary),samples=len(rows),cv_over_10pct=sum(r['cv']>.1 for r in summary),
             major_faults=sum(r['major_faults'] for r in summary),swap_in_pages=mon[-1]['pswpin']-mon[0]['pswpin'],
             swap_out_pages=mon[-1]['pswpout']-mon[0]['pswpout'],min_available_kib=min(r['MemAvailable'] for r in mon))
(root/'quality.json').write_text(json.dumps(quality,indent=2)+'\n');print(json.dumps(quality),flush=True)
lines=['# P3 measurements','','| Mode | P | G | B | Threads | Median ms | Aggregate tokens/s | Per sequence tokens/s | CV |',
       '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in sorted(summary,key=lambda r:(r['mode'],r['P'],r['B'],r['threads'])):
    lines.append(f"| {r['mode']} | {r['P']} | {r['G']} | {r['B']} | {r['threads']} | {r['median_ms']:.2f} | {r['tokens_s']:.2f} | {r['per_sequence_tokens_s']:.2f} | {r['cv']:.1%} |")
(root/'measurements.md').write_text('\n'.join(lines)+'\n')
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for t in [1,2,4]:
        ds=sorted([r for r in summary if r['mode']=='prefill' and r['threads']==t],key=lambda r:r['P'])
        if ds:axes[0].plot([r['P'] for r in ds],[r['tokens_s'] for r in ds],'-o',label=f'{t} threads')
    axes[0].set(xlabel='Prompt tokens',ylabel='Prefill tokens/s',title='Falcon3 1B I2_V_4 / prefill');axes[0].legend();axes[0].grid(alpha=.2)
    ds=sorted([r for r in summary if r['mode']=='decode' and r['threads']==4],key=lambda r:r['B'])
    axes[1].plot([r['B'] for r in ds],[r['tokens_s'] for r in ds],'-o',label='Aggregate')
    axes[1].plot([r['B'] for r in ds],[r['per_sequence_tokens_s'] for r in ds],'-o',label='Per sequence')
    axes[1].set(xlabel='Parallel sequences (shared prefix)',ylabel='Decode tokens/s',title='4 threads / 128-token prefix');axes[1].legend();axes[1].grid(alpha=.2)
    fig.tight_layout();fig.savefig(root/'performance.png',dpi=180);plt.close(fig)
except ImportError:print('Optional matplotlib unavailable; CSV/Markdown complete')
