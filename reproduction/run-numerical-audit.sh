#!/usr/bin/env bash
# Optional diagnostics, deliberately separate from all performance runners.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
root="${VECLUT_REPRO_DIR:-$repo/.repro}"
root="$(realpath "$root")"
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/cache" PYTHONPYCACHEPREFIX="$root/cache/pycache"
export OMP_WAIT_POLICY=PASSIVE OMP_DYNAMIC=FALSE OMP_PROC_BIND=CLOSE
export OMP_PLACES="${P3_OMP_PLACES:-}"
[[ -n "$OMP_PLACES" ]] || export OMP_PLACES='{0},{2},{4},{6}'
unset P3_AUDIT_LOGITS P3_AUDIT_NODES P3_AUDIT_STEP
binary="$root/builds/p2-normal/bin/bench-p3"
model="$root/models/bitnet-3b-i2v4/ggml-model-I2_V_4.gguf"
[[ -x "$binary" && -f "$model" ]] || { echo 'Run P3 with --model bitnet-3b-i2v4 first';exit 1; }
run="$root/results/bitnet-numerical-audit-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$run"
exec > >(tee "$run/session.log") 2>&1
echo "Numerical audit evidence: $run (not performance measurements)"
git -C "$repo" rev-parse HEAD > "$run/source-sha.txt"
git -C "$repo" diff --binary > "$run/source.patch"
sha256sum "$binary" "$root/builds/p2-normal/src/libllama.so" "$root/builds/p2-normal/ggml/src/"*.so > "$run/binaries.sha256"
cp "$root/models/bitnet-3b-i2v4/model-manifest.json" "$run/model-manifest.json"
for B in 1 4; do
  P3_AUDIT_LOGITS="$run/B$B" "$binary" "$model" smoke 32 4 "$B" 4 1 > "$run/logits-B$B.jsonl" 2> "$run/logits-B$B.stderr.log"
done
python3 "$repo/reproduction/analyze_logits.py" "$run"
for step in 0 1; do
  P3_AUDIT_STEP="$step" P3_AUDIT_NODES="$run/nodes-step$step.jsonl" \
    "$binary" "$model" smoke 32 2 4 4 1 > "$run/nodes-step$step-run.jsonl" 2> "$run/nodes-step$step.stderr.log"
done
echo 'Audit complete. Interpret the node and quantization deltas using BITNET_NUMERICAL_AUDIT.md.'
