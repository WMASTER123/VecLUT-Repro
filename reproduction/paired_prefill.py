"""Resident, serialized OFF/ON workers with per-sample affinity evidence.

Usage: paired_prefill.py DATA_DIR OUTPUT_DIR PLAN_JSON
The two models are resident simultaneously; only one worker receives RUN at a time.
"""
import json
import os
from pathlib import Path
import select
import statistics
import subprocess
import sys
import time

from run_p6 import memory
from model_registry import MODELS


class Worker:
    def __init__(self, root, run, label, case, variant):
        self.log = (run / f"{label}.jsonl").open("w")
        self.err = (run / f"{label}.stderr.log").open("w")
        env = os.environ.copy()
        for key in list(env):
            if key.startswith("P3_AUDIT_") or key in ("GOMP_CPU_AFFINITY", "KMP_AFFINITY"):
                env.pop(key)
        cpus = case.get("cpus", [0])
        env.update(P6_SAMPLE_CONTROL="1", OMP_WAIT_POLICY="PASSIVE", OMP_DYNAMIC="FALSE",
                   OMP_PROC_BIND="CLOSE", OMP_NUM_THREADS=str(case.get("threads", 1)),
                   OMP_PLACES=",".join("{"+str(c)+"}" for c in (cpus if case.get("fixed", True) else [0, 2, 4, 6])))
        env.update(TMPDIR=str(root/"tmp"), XDG_CACHE_HOME=str(root/"cache"))
        binary = root / "builds" / f"p6-{variant}" / "bin/bench-p6r-model"
        model = root / "models" / case["model"] / MODELS[case["model"]]["file"]
        args = [str(binary), str(model), case.get("mode", "prefill"), str(case["P"]),
                str(case.get("G", 0)), str(case.get("B", 1)), str(case.get("threads", 1)), str(case.get("samples", 10))]
        if case.get("fixed", True):
            args = ["taskset", "--cpu-list", ",".join(map(str, cpus))] + args
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.err, text=True, bufsize=1, env=env)
        self.args = args
        try:
            self.setup = self.read()
            if self.setup["record"] != "setup" or self.setup["profile"] or not self.setup.get("controlled"):
                raise RuntimeError("invalid worker setup")
        except BaseException:
            self.close()
            raise

    def read(self):
        if not select.select([self.proc.stdout], [], [], 120)[0]:
            raise TimeoutError("worker response timeout")
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError(f"worker exited: {self.proc.poll()}")
        self.log.write(line); self.log.flush()
        return json.loads(line)

    def step(self):
        self.proc.stdin.write("RUN\n"); self.proc.stdin.flush()
        return self.read()

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
        self.proc.wait(timeout=10)
        self.log.close(); self.err.close()


def main():
    root, run, plan_path = map(Path, sys.argv[1:4])
    run.mkdir(parents=True, exist_ok=False)
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    (run/"plan.json").write_text(json.dumps(plan, indent=2))
    results = []
    for case_id, case in enumerate(plan):
        count = case.get("samples", 10)
        if count < 6 or count % 2:
            raise ValueError("use an even sample count >=6")
        variants = case.get("variants", ["off", "on"])
        if len(variants) != 2:
            raise ValueError("exactly two variants required")
        workers = {}
        try:
            for variant in variants:
                workers[variant] = Worker(root, run, f"case{case_id}-{variant}", case, variant)
            (run/f"case{case_id}-workers.json").write_text(json.dumps(
                {v: dict(pid=w.proc.pid, args=w.args, setup=w.setup) for v,w in workers.items()}, indent=2))
            for worker in workers.values():
                if worker.step()["record"] != "warmup":
                    raise RuntimeError("missing warmup")
            case_rows = []
            for block in range(count//2):
                a, b = variants if block % 2 == 0 else variants[::-1]
                for variant in (a, b, b, a):
                    before = memory(); started = time.time()
                    row = workers[variant].step(); after = memory()
                    if row["record"] != "sample" or not row["finite_logits"] or row["major_faults"]:
                        raise RuntimeError("invalid sample")
                    for key in ("scheduling_before", "scheduling_after_prefill"):
                        snapshot = row[key]
                        if snapshot["migrations"] < 0 or snapshot["runtime_ns"] <= 0 or snapshot["timeslices"] <= 0:
                            raise RuntimeError("scheduling telemetry unavailable; cannot treat missing values as zero")
                    if any(before[k] != after[k] for k in ("pswpin", "pswpout")):
                        raise RuntimeError("swap observed")
                    if case.get("fixed", True) and case.get("threads", 1) == 1:
                        for key in ("scheduling_before", "scheduling_after_prefill"):
                            if row[key]["allowed_cpus"] != case.get("cpus", [0]) or row[key]["cpu"] not in case.get("cpus", [0]):
                                raise RuntimeError("affinity escaped requested CPU")
                    enriched = dict(case_id=case_id, case=case, variant=variant, block=block,
                                    start_unix=started, end_unix=time.time(), memory_before=before,
                                    memory_after=after, **row)
                    case_rows.append(enriched); results.append(enriched)
                    with (run/"samples.jsonl").open("a") as f:
                        f.write(json.dumps(enriched)+"\n")
                print(f"case {case_id} {case['model']} P{case['P']} block {block+1}/{count//2} passed", flush=True)
            if case.get("threads", 1) == 1 and len({s["last_logits_hash"] for s in case_rows}) != 1:
                raise RuntimeError("single-thread logits hashes differ")
            if len({json.dumps(s["output_token_ids"]) for s in case_rows}) != 1:
                raise RuntimeError("generated tokens differ")
            for worker in workers.values():
                if worker.proc.wait(timeout=15) != 0:
                    raise RuntimeError("worker failed after measurements")
        finally:
            for worker in workers.values():
                worker.close()
    summaries = []
    for case_id, case in enumerate(plan):
        metric = "decode_loop_ms" if case.get("mode") == "decode" else "prefill_ms"
        values = {}
        for v in case.get("variants", ["off", "on"]):
            rows = [s for s in results if s["case_id"] == case_id and s["variant"] == v]
            lat = [s[metric] for s in rows]
            ratios = [s["prefill_cpu_ms"]/s["prefill_ms"] for s in rows]
            values[v] = dict(median_ms=statistics.median(lat), cv=statistics.stdev(lat)/statistics.mean(lat),
                cpu_wall_ratio=statistics.median(ratios),
                migrations=sum(s["scheduling_after_prefill"]["migrations"]-s["scheduling_before"]["migrations"] for s in rows),
                wait_ms=statistics.median((s["scheduling_after_prefill"]["runnable_wait_ns"]-s["scheduling_before"]["runnable_wait_ns"])/1e6 for s in rows))
        a,b=case.get("variants", ["off", "on"])
        summaries.append(dict(case_id=case_id, case=case, values=values, speedup=values[a]["median_ms"]/values[b]["median_ms"]))
    (run/"summary.json").write_text(json.dumps(summaries, indent=2))
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
