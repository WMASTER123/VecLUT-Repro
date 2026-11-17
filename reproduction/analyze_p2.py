import argparse, csv, json, statistics as st
from collections import defaultdict
from pathlib import Path

def summarize(path):
    rows=list(csv.DictReader((path/'raw.csv').open())); groups=defaultdict(list)
    for row in rows: groups[(row['shape'],row['mode'],int(row['N']),int(row['threads']))].append(row)
    result=[]
    for (shape,mode,n,t),g in sorted(groups.items()):
        v=[float(r['wall_us']) for r in g]; q=st.quantiles(v,n=4,method='inclusive'); med=st.median(v)
        d=dict(shape=shape,mode=mode,M=int(g[0]['M']),K=int(g[0]['K']),N=n,threads=t,samples=len(v),
               median_us=med,min_us=min(v),max_us=max(v),iqr_us=q[2]-q[0],cv=st.stdev(v)/st.mean(v),
               runs_s=1e6/med,ns_per_effective_mac=med*1000/(int(g[0]['M'])*int(g[0]['K'])*n),
               padding_utilization=n/int(g[0]['padded_N']),peak_process_kib=max(int(r['peak_process_kib']) for r in g),
               major_faults=sum(int(r['major_faults']) for r in g),minor_faults=sum(int(r['minor_faults']) for r in g),
               involuntary_switches=sum(int(r['involuntary_switches']) for r in g))
        for key in g[0]:
            if key.endswith('_worker_us'): d[key]=st.median(float(r[key]) for r in g)
        result.append(d)
    with (path/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(result[0])); w.writeheader(); w.writerows(result)
    monitor=[json.loads(s) for s in (path/'monitor.jsonl').read_text().splitlines()]
    quality=dict(configurations=len(result),samples=len(rows),cv_over_10pct=sum(x['cv']>.1 for x in result),
                 main_thread_migrations=sum(r.get('main_cpu_before')!=r.get('main_cpu_after') for r in rows),
                 major_faults=sum(x['major_faults'] for x in result),
                 swap_in_pages=monitor[-1]['pswpin']-monitor[0]['pswpin'],swap_out_pages=monitor[-1]['pswpout']-monitor[0]['pswpout'],
                 min_available_kib=min(x['MemAvailable'] for x in monitor))
    (path/'quality.json').write_text(json.dumps(quality,indent=2)+'\n')
    print(path.name,json.dumps(quality))
    lines=['# P2 measurements','', 'Single matrix operator; synthetic inputs; not end-to-end model tokens/s.','',
           '| shape | mode | N | threads | median us | CV |','|---|---|---:|---:|---:|---:|']
    lines += [f"| {d['shape']} | {d['mode']} | {d['N']} | {d['threads']} | {d['median_us']:.2f} | {d['cv']:.1%} |" for d in result]
    (path/'measurements.md').write_text('\n'.join(lines)+'\n')
    return result

def plots(root,results):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('Optional matplotlib unavailable; CSV/Markdown analysis is complete.'); return
    plt.rcParams.update({'font.size':10,'figure.facecolor':'white','axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(1,2,figsize=(12,4.4))
    for ax,shape in zip(axs,['falcon_square','bitnet_square']):
        for t in [1,2,4]:
            ds=sorted([r for r in results if r['shape']==shape and r['mode']=='graph' and r['threads']==t],key=lambda r:r['N'])
            ax.errorbar([r['N'] for r in ds],[r['median_us']/1000 for r in ds],yerr=[r['iqr_us']/2000 for r in ds],marker='o',label=f'{t} threads')
        ax.set(xscale='log',yscale='log',xlabel='Tokens N',ylabel='Single operator latency (ms)',title=shape)
        ax.grid(alpha=.2); ax.legend()
    fig.tight_layout(); fig.savefig(root/'latency.png',dpi=180); fig.savefig(root/'latency.svg'); plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,4))
    for ax,shape in zip(axs,['falcon_square','bitnet_square']):
        for t in [1,2,4]:
            ds=sorted([r for r in results if r['shape']==shape and r['mode']=='graph' and r['threads']==t and r['N']<=65],key=lambda r:r['N'])
            ax.plot([r['N'] for r in ds],[r['median_us'] for r in ds],'-o',label=f'{t} threads')
        ax.set(xlabel='Tokens N',ylabel='Single operator latency (us)',title=shape+' / tile boundaries')
        ax.grid(alpha=.2); ax.legend()
    fig.tight_layout(); fig.savefig(root/'tails.png',dpi=180); fig.savefig(root/'tails.svg'); plt.close(fig)

def phase_plot(root, results):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return
    ds=[r for r in results if r['mode']=='graph' and r['threads']==1]
    keys=['alloc_init','build','lookup','widen','output','free','activation']
    totals=[sum(r[k+'_worker_us'] for k in keys) for r in ds]
    fig,ax=plt.subplots(figsize=(11,5)); left=[0.0]*len(ds)
    for k in keys:
        values=[100*r[k+'_worker_us']/total for r,total in zip(ds,totals)]
        ax.barh(range(len(ds)),values,left=left,label=k)
        left=[a+b for a,b in zip(left,values)]
    ax.set_yticks(range(len(ds)),[r['shape']+' N='+str(r['N']) for r in ds])
    ax.set(xlabel='Share of instrumented worker elapsed time (%)',xlim=(0,100),title='I2_V_4 diagnostic phases / 1 thread')
    ax.legend(ncol=4,loc='upper center',bbox_to_anchor=(.5,-.12))
    fig.tight_layout(); fig.savefig(root/'phases.png',dpi=180); fig.savefig(root/'phases.svg'); plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('root',type=Path); a=p.parse_args()
    for name in ['normal','profile']:
        path=a.root/name
        if path.exists():
            result=summarize(path)
            if name=='normal': plots(a.root,result)
            else: phase_plot(a.root,result)
