"""Compare opt-in smoke logit dumps without third-party Python dependencies."""
import array
import json
import sys
from pathlib import Path

root=Path(sys.argv[1])
report=[]
for step in range(4):
    rows=[]
    for batch in (1,4):
        data=array.array('f')
        data.frombytes((root/f'B{batch}-r0-s{step}.bin').read_bytes())
        vocab=len(data)//batch
        rows.append([data[i*vocab:(i+1)*vocab] for i in range(batch)])
    ref=rows[0][0]
    record={'step':step,'vocab':len(ref),'comparisons':[]}
    for i,row in enumerate(rows[1]):
        top=sorted(range(len(row)),key=lambda j:row[j],reverse=True)[:2]
        record['comparisons'].append(dict(lane=i,max_abs_vs_B1=max(abs(a-b) for a,b in zip(row,ref)),
            max_abs_vs_lane0=max(abs(a-b) for a,b in zip(row,rows[1][0])),top=top,margin=row[top[0]]-row[top[1]]))
    report.append(record)
text=json.dumps(report,indent=2)+'\n'
(root/'logit-comparison.json').write_text(text)
print(text)
