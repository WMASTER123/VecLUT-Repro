"""Diagnostic-only real-model routing proof; never use these timings as performance."""
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    root, out = map(Path, sys.argv[1:3])
    out.mkdir(parents=True, exist_ok=False)
    cases = [("bitnet-3b-i2v4",p,1,"prefill",0) for p in (16,32,33,128)]
    cases += [("bitnet-3b-i2v4",128,4,"prefill",0),
              ("falcon3-1b-i2v4",128,1,"prefill",0),
              ("bitnet-3b-i2v4",32,1,"decode",2)]
    results=[]
    for i,(model,p,threads,mode,g) in enumerate(cases):
        cpus=[2] if threads==1 else [0,2,4,6]
        env=os.environ.copy();env.pop("P6_SAMPLE_CONTROL",None)
        env.update(OMP_PLACES=",".join("{"+str(c)+"}" for c in cpus),OMP_PROC_BIND="CLOSE",
                   OMP_WAIT_POLICY="PASSIVE",OMP_DYNAMIC="FALSE",OMP_NUM_THREADS=str(threads))
        args=["taskset","-c",",".join(map(str,cpus)),str(root/"builds/p6-selected-profile/bin/bench-p6r-model"),
              str(root/"models"/model/"ggml-model-I2_V_4.gguf"),mode,str(p),str(g),"1",str(threads),"1"]
        with (out/f"case{i}.jsonl").open("w") as f,(out/f"case{i}.stderr.log").open("w") as err:
            subprocess.run(args,env=env,stdout=f,stderr=err,check=True)
        records=[json.loads(line) for line in (out/f"case{i}.jsonl").read_text().splitlines()]
        setup=next(x for x in records if x["record"]=="setup")
        sample=next(x for x in records if x["record"]=="sample")
        expected=179 if model.startswith("bitnet") and p>=32 and threads==1 else 0
        expected_calls=(182 if model.startswith("bitnet") else 126)*threads
        assert setup["profile"] and sample["prefill_i2v4_worker_calls"]==expected_calls
        assert sample["prefill_widen"]["selected_kernel_calls"]==expected
        assert bool(sample["prefill_widen"]["blocked_calls"])==bool(expected)
        assert sample["prefill_widen"]["plain_calls"]>0
        if mode=="decode":
            assert sample["final_widen"]["selected_kernel_calls"]==0 and sample["final_widen"]["blocked_calls"]==0
        results.append(dict(model=model,P=p,threads=threads,mode=mode,passed=True,
                            expected_selected=expected,prefill=sample["prefill_widen"],final=sample["final_widen"]))
        print(f"path case {i}: selected {expected}/{expected_calls}, passed",flush=True)
    (out/"summary.json").write_text(json.dumps(results,indent=2))


if __name__=="__main__":main()
