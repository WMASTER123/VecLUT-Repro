"""Paired own-system experiment, OFF/ON order reversed in the second batch."""
import csv
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time


def memory():
    result = {}
    for name in ("meminfo", "vmstat"):
        for line in Path("/proc", name).read_text().splitlines():
            key, value, *_ = line.replace(":", "").split()
            if key in ("MemAvailable", "pswpin", "pswpout"):
                result[key] = int(value)
    return result


def main():
    root, run = map(Path, sys.argv[1:3])
    cases = [(3200, 3200, 1, 4), (3200, 3200, 32, 1), (3200, 3200, 128, 1),
             (3200, 3200, 128, 4), (8640, 3200, 128, 1), (3200, 8640, 128, 4),
             (8192, 2048, 33, 4), (17, 144, 33, 4)]
    manifest = {"cases": cases, "repeats": 5, "target_ms": 1000,
                "orders": [["off", "on"], ["on", "off"]],
                "scope": "bounded motivation gate; not the full P2 matrix",
                "omp_places": os.environ.get("OMP_PLACES"), "before": memory()}
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2))
    samples = []
    for batch, order in enumerate(manifest["orders"]):
        for case_id in (range(len(cases)) if batch == 0 else reversed(range(len(cases)))):
            m, k, n, threads = cases[case_id]
            for variant in order:
                label = f"batch{batch}-case{case_id}-{variant}"
                args = [str(root / "builds" / f"p6-{variant}" / "bin/bench-p2"),
                        str(m), str(k), str(n), "5", "1000", f"graph{threads}"]
                start = time.time()
                before = memory()
                with (run / f"{label}.csv").open("w") as output, (run / f"{label}.log").open("w") as err:
                    subprocess.run(args, stdout=output, stderr=err, check=True)
                after = memory()
                (run / f"{label}-resources.json").write_text(json.dumps(
                    {"args": args, "start_unix": start, "elapsed_s": time.time()-start,
                     "before": before, "after": after}, indent=2))
                rows = list(csv.DictReader((run / f"{label}.csv").open()))
                if len(rows) != 5 or any(int(row["profile"]) for row in rows):
                    raise RuntimeError("unexpected measurement count/profile")
                if after["pswpin"] != before["pswpin"] or after["pswpout"] != before["pswpout"]:
                    raise RuntimeError("swap activity; preserve evidence and investigate")
                if any(int(row["major_faults"]) for row in rows):
                    raise RuntimeError("major faults during timing")
                for row in rows:
                    samples.append(dict(batch=batch, case_id=case_id, variant=variant, **row))
                print(label + " passed", flush=True)
    with (run / "samples.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, samples[0].keys()); writer.writeheader(); writer.writerows(samples)
    summary = []
    for case_id, case in enumerate(cases):
        entry = dict(case_id=case_id, M=case[0], K=case[1], N=case[2], threads=case[3], batches=[])
        for batch in range(2):
            values = {v: [float(s["wall_us"]) for s in samples
                          if s["case_id"] == case_id and s["batch"] == batch and s["variant"] == v]
                      for v in ("off", "on")}
            med = {v: statistics.median(x) for v, x in values.items()}
            entry["batches"].append(dict(batch=batch, median_us=med,
                speedup=med["off"]/med["on"],
                cv={v: statistics.stdev(x)/statistics.mean(x) for v, x in values.items()}))
        summary.append(entry)
    (run / "summary.json").write_text(json.dumps(summary, indent=2))
    lines = ["# P6 paired graph latency", "", "OFF/ON are the same corrected system; 5 samples per variant per batch.", "",
             "| M,K,N,T | Batch 1 OFF/ON us | Speedup | Batch 2 OFF/ON us | Speedup | Max CV |",
             "|---|---:|---:|---:|---:|---:|"]
    for s in summary:
        a, b = s["batches"]
        cv = max(*a["cv"].values(), *b["cv"].values())
        lines.append(f'| {s["M"]},{s["K"]},{s["N"]},{s["threads"]} | '
                     f'{a["median_us"]["off"]:.2f}/{a["median_us"]["on"]:.2f} | {a["speedup"]:.3f}x | '
                     f'{b["median_us"]["off"]:.2f}/{b["median_us"]["on"]:.2f} | {b["speedup"]:.3f}x | {cv:.1%} |')
    (run / "summary.md").write_text("\n".join(lines)+"\n")
    # Diagnostic timers are kept separate from all uninstrumented wall-time data.
    for case_id in (0, 2, 3, 4):
        m, k, n, threads = cases[case_id]
        for variant in ("off", "on"):
            args = [str(root / "builds" / f"p6-profile-{variant}" / "bin/bench-p2"),
                    str(m), str(k), str(n), "5", "200", f"graph{threads}"]
            with (run / f"profile-case{case_id}-{variant}.csv").open("w") as output, \
                 (run / f"profile-case{case_id}-{variant}.log").open("w") as err:
                subprocess.run(args, stdout=output, stderr=err, check=True)
    manifest["after"] = memory()
    (run / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
