"""Use the same production libllama driver for OFF/ON whole-model timings."""
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

from run_p6 import memory


def main():
    root, run = map(Path, sys.argv[1:3])
    models = ("falcon3-1b-i2v4", "bitnet-3b-i2v4")
    cases = [(model, mode, threads) for model in models
             for mode, threads in (("prefill", 1), ("prefill", 4), ("decode", 4))]
    (run / "manifest.json").write_text(json.dumps(dict(cases=cases, P=128, G=16, B=1,
        repeats=5, orders=[["off", "on"], ["on", "off"]],
        note="G=16 confirmation workload, separate from P3/P4 G=32 baseline",
        affinity={k: os.environ.get(k) for k in ("OMP_PLACES", "OMP_PROC_BIND", "OMP_WAIT_POLICY", "OMP_DYNAMIC")}), indent=2))

    def execute(label, model, mode, threads, variant, repeats):
        model_path = root / "models" / model / "ggml-model-I2_V_4.gguf"
        args = [str(root / "builds" / f"p6-{variant}" / "bin/bench-p3"), str(model_path),
                mode, "128", "0" if mode == "prefill" else "16", "1", str(threads), str(repeats)]
        before = memory(); start = time.time()
        with (run / f"{label}.jsonl").open("w") as output, (run / f"{label}.stderr.log").open("w") as err:
            subprocess.run(args, stdout=output, stderr=err, check=True)
        after = memory()
        (run / f"{label}-resources.json").write_text(json.dumps(
            dict(args=args, start_unix=start, elapsed_s=time.time()-start, before=before, after=after), indent=2))
        records = [json.loads(line) for line in (run / f"{label}.jsonl").read_text().splitlines() if line.startswith('{')]
        setup = next(record for record in records if record["record"] == "setup")
        if setup.get("profile", False):
            raise RuntimeError("instrumented binary used for performance")
        rows = [record for record in records if record["record"] == "sample"]
        if len(rows) != repeats or any(not row["finite_logits"] or row["major_faults"] for row in rows):
            raise RuntimeError("invalid model measurement")
        if any(before[k] != after[k] for k in ("pswpin", "pswpout")):
            raise RuntimeError("swap activity")
        return rows

    # Generated token equivalence is also checked when Prefill has no output tokens.
    for model in models:
        outputs = {variant: execute(f"smoke-{model}-{variant}", model, "smoke", 4, variant, 1)[0]
                   for variant in ("off", "on")}
        if not outputs["off"]["output_token_ids"][0] or outputs["off"]["output_token_ids"] != outputs["on"]["output_token_ids"]:
            raise RuntimeError("OFF/ON smoke token mismatch")
    summaries = []
    for batch, order in enumerate((("off", "on"), ("on", "off"))):
        for case_id in (range(len(cases)) if batch == 0 else reversed(range(len(cases)))):
            model, mode, threads = cases[case_id]
            values = {}; outputs = {}
            for variant in order:
                label = f"batch{batch}-case{case_id}-{variant}"
                rows = execute(label, model, mode, threads, variant, 5)
                key = "prefill_ms" if mode == "prefill" else "decode_loop_ms"
                latency = [row[key] for row in rows]
                med = statistics.median(latency)
                values[variant] = dict(median_ms=med, cv=statistics.stdev(latency)/statistics.mean(latency),
                                       tokens_s=(128 if mode == "prefill" else 16)*1000/med)
                outputs[variant] = [row["output_token_ids"] for row in rows]
                print(label + " passed", flush=True)
            if outputs["off"] != outputs["on"]:
                raise RuntimeError("OFF/ON generated tokens differ")
            summaries.append(dict(batch=batch, case_id=case_id, model=model, mode=mode, threads=threads,
                                  values=values, speedup=values["off"]["median_ms"]/values["on"]["median_ms"],
                                  same_tokens=True))
    (run / "summary.json").write_text(json.dumps(summaries, indent=2))
    lines = ["# P6 model OFF/ON confirmation", "",
             "P=128, B=1; Decode G=16; 5 samples per variant per batch. Model loading excluded.", "",
             "| Model / mode / threads | Batch 1 OFF/ON tokens/s | Speedup | Batch 2 OFF/ON tokens/s | Speedup | Max CV |",
             "|---|---:|---:|---:|---:|---:|"]
    for case_id, (model, mode, threads) in enumerate(cases):
        a, b = sorted((s for s in summaries if s["case_id"] == case_id), key=lambda s: s["batch"])
        cv = max(s["values"][v]["cv"] for s in (a, b) for v in ("off", "on"))
        lines.append(f'| {model} / {mode} / {threads} | '
                     f'{a["values"]["off"]["tokens_s"]:.2f}/{a["values"]["on"]["tokens_s"]:.2f} | {a["speedup"]:.3f}x | '
                     f'{b["values"]["off"]["tokens_s"]:.2f}/{b["values"]["on"]["tokens_s"]:.2f} | {b["speedup"]:.3f}x | {cv:.1%} |')
    (run / "summary.md").write_text("\n".join(lines)+"\n")


if __name__ == "__main__":
    main()
