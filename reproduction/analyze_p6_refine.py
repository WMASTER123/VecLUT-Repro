"""Summarize all refinement evidence without excluding slow samples.

Usage: analyze_p6_refine.py AFFINITY_RUN SCREEN_RUN SELECTIVE_RUN OUTPUT_DIR
Block ranges describe the observed blocks; they are not confidence intervals.
"""
import csv
import json
from pathlib import Path
import statistics
import sys


def paired(run):
    rows = [json.loads(line) for line in (run / "paired/samples.jsonl").read_text().splitlines()]
    summary = json.loads((run / "paired/summary.json").read_text())
    for item in summary:
        case = item["case"]
        variants = case.get("variants", ["off", "on"])
        metric = "decode_loop_ms" if case.get("mode") == "decode" else "prefill_ms"
        samples = [r for r in rows if r["case_id"] == item["case_id"]]
        blocks = []
        for block in sorted({r["block"] for r in samples}):
            values = {v: statistics.median(r[metric] for r in samples
                      if r["variant"] == v and r["block"] == block) for v in variants}
            blocks.append(values[variants[0]] / values[variants[1]])
        item["block_speedups"] = blocks
        item["block_range_is_not_ci"] = True
        item["sample_count"] = len(samples)
        item["major_faults"] = sum(r["major_faults"] for r in samples)
        item["swap_changed_samples"] = sum(any(r["memory_before"][k] != r["memory_after"][k]
                                                 for k in ("pswpin", "pswpout")) for r in samples)
        item["token_variants"] = len({json.dumps(r["output_token_ids"]) for r in samples})
        item["logit_hash_variants"] = len({r["last_logits_hash"] for r in samples})
    return summary


def main():
    affinity, screen, selective, out = map(Path, sys.argv[1:5])
    out.mkdir(parents=True, exist_ok=False)
    cases = json.loads((screen / "screen/summary.json").read_text())
    with (out / "all-shapes.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["M", "K", "N", "threads", "speedup_batch0", "speedup_batch1", "both_gt_1.02", "both_lt_0.98"])
        for c in cases:
            ratios = [b["speedup"] for b in c["batches"]]
            writer.writerow([c[k] for k in ("M", "K", "N", "threads")] + ratios +
                            [all(x > 1.02 for x in ratios), all(x < .98 for x in ratios)])
    paths = json.loads((selective / "path-check/summary.json").read_text())
    for p in paths:
        d = p["prefill"]
        p["blocked_element_fraction"] = d["blocked_elements"] / (d["blocked_elements"] + d["plain_elements"])
    result = dict(affinity=paired(affinity), selective=paired(selective), paths=paths,
                  screen_configurations=len(cases), screen_samples=sum(1 for _ in
                  csv.DictReader((screen / "screen/samples.csv").open())))
    (out / "summary.json").write_text(json.dumps(result, indent=2))
    lines = ["# P6 refinement: generated statistics", "", "No samples excluded. Speedup = baseline median / candidate median.",
             "Block ranges are descriptive, not confidence intervals.", ""]
    for name in ("affinity", "selective"):
        lines += ["## " + name, "", "|case|model|P|threads|mode|OFF ms|candidate ms|speedup|block range|CV OFF/candidate|", "|---|---|---|---|---|---|---|---|---|---|"]
        for s in result[name]:
            c = s["case"]; a, b = c.get("variants", ["off", "on"])
            x, y = s["values"][a], s["values"][b]
            blocks = s["block_speedups"]
            lines.append(f"|{s['case_id']}|{c['model']}|{c['P']}|{c.get('threads', 1)}|{c.get('mode', 'prefill')}|{x['median_ms']:.3f}|{y['median_ms']:.3f}|{s['speedup']:.4f}|{min(blocks):.4f}–{max(blocks):.4f}|{x['cv']:.2%}/{y['cv']:.2%}|")
        lines.append("")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("Analysis saved:", out)


if __name__ == "__main__":
    main()
