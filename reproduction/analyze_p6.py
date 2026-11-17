"""Summarize sequential repeatability and diagnostic phases without selecting best runs."""
import csv
import json
import math
from pathlib import Path
import random
import statistics
import sys


def main():
    run = Path(sys.argv[1])
    samples = list(csv.DictReader((run / "samples.csv").open()))
    summary = json.loads((run / "summary.json").read_text())
    rng = random.Random(20261117)
    lines = ["# P6 uncertainty and phase diagnostics", "",
             "Bootstrap intervals are descriptive within this session, not independent multi-day evidence.",
             "Each batch is resampled separately; ratio is the geometric mean of the two median latency ratios.", "",
             "| M,K,N,T | Speedup | Descriptive 95% interval |", "|---|---:|---:|"]
    uncertainty = []
    for case in summary:
        groups = {(batch, variant): [float(s["wall_us"]) for s in samples
                  if int(s["case_id"]) == case["case_id"] and int(s["batch"]) == batch and s["variant"] == variant]
                  for batch in (0, 1) for variant in ("off", "on")}
        if any(len(x) != 5 for x in groups.values()):
            raise ValueError("incomplete paired data")
        boot = []
        for _ in range(5000):
            ratios = []
            for batch in (0, 1):
                med = {v: statistics.median(rng.choices(groups[batch, v], k=5)) for v in ("off", "on")}
                ratios.append(med["off"] / med["on"])
            boot.append(math.sqrt(ratios[0] * ratios[1]))
        boot.sort()
        ratio = math.sqrt(case["batches"][0]["speedup"] * case["batches"][1]["speedup"])
        lo, hi = boot[124], boot[4874]
        uncertainty.append(dict(case_id=case["case_id"], speedup=ratio, interval95=[lo, hi]))
        lines.append(f'| {case["M"]},{case["K"]},{case["N"]},{case["threads"]} | {ratio:.3f}x | [{lo:.3f}, {hi:.3f}] |')
    lines += ["", "All phase values below are summed worker microseconds, with instrumentation enabled.",
              "They are not formal wall-time speedups.", "",
              "| Case | OFF widen | ON widen | OFF clear | ON clear |", "|---|---:|---:|---:|---:|"]
    phases = []
    for case_id in (0, 2, 3, 4):
        item = dict(case_id=case_id)
        for v in ("off", "on"):
            rows = list(csv.DictReader((run / f"profile-case{case_id}-{v}.csv").open()))
            if len(rows) != 5 or any(int(row["profile"]) != 1 for row in rows):
                raise ValueError("unexpected profile data")
            item[v] = {phase: statistics.median(float(row[phase]) for row in rows)
                       for phase in ("widen_worker_us", "clear_worker_us")}
        phases.append(item)
        lines.append(f'| {case_id} | {item["off"]["widen_worker_us"]:.2f} | {item["on"]["widen_worker_us"]:.2f} | '
                     f'{item["off"]["clear_worker_us"]:.2f} | {item["on"]["clear_worker_us"]:.2f} |')
    (run / "analysis.md").write_text("\n".join(lines)+"\n")
    (run / "analysis.json").write_text(json.dumps(dict(uncertainty=uncertainty, phases=phases), indent=2))


if __name__ == "__main__":
    main()
