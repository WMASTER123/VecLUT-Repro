#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
root="$(realpath "${VECLUT_REPRO_DIR:-$repo/.repro}")"
plan="${1:-$repo/reproduction/plans/affinity.json}"
run="${2:-$root/results/p6-refine-$(date +%Y%m%d-%H%M%S)-$$}"
mkdir -p "$run"
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/cache" PYTHONPYCACHEPREFIX="$root/cache/pycache"
export OMP_WAIT_POLICY=PASSIVE
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME"
exec > >(tee "$run/session.log") 2>&1
echo "Evidence: $run"
git -C "$repo" rev-parse HEAD > "$run/source-sha.txt"
git -C "$repo" diff --binary > "$run/source.patch"
git -C "$repo" status --short > "$run/git-status.txt"
{ date -Is; uname -srvm; lscpu; free -b; c++ --version; } > "$run/environment.txt"
mapfile -t variants < <(python3 -c 'import json,sys;print("\n".join(sorted({v for c in json.load(open(sys.argv[1])) for v in c.get("variants",["off","on"])})))' "$plan")
mapfile -t models < <(python3 -c 'import json,sys;print("\n".join(sorted({c["model"] for c in json.load(open(sys.argv[1]))})))' "$plan")
for model in "${models[@]}"; do
  python3 "$repo/reproduction/prepare_model_p3.py" "$root" "$model" > "$run/$model-verification.log"
  cp "$root/models/$model/model-manifest.json" "$run/$model-manifest.json"
done
for variant in "${variants[@]}"; do
  case "$variant" in off|on|selected) ;; *) echo 'Unsupported variant'; exit 1;; esac
  build="$root/builds/p6-$variant"
  flag=OFF; [[ "$variant" != on ]] || flag=ON
  for option in "VLUT_I2V4_BLOCKED_WIDEN:BOOL=$flag" 'VLUT_PROFILE:BOOL=OFF' 'CMAKE_BUILD_TYPE:STRING=Release'; do
    grep -qx "$option" "$build/CMakeCache.txt" || { echo 'Run P6 builds first'; exit 1; }
  done
  selective=$(sed -n 's/^VLUT_I2V4_SELECTIVE_WIDEN:BOOL=//p' "$build/CMakeCache.txt")
  expected_selective=OFF; [[ "$variant" != selected ]] || expected_selective=ON
  [[ "${selective:-OFF}" == "$expected_selective" ]] || { echo 'Unexpected selector configuration'; exit 1; }
  bash "$repo/reproduction/compile-p3.sh" "$build" "$build/bin/bench-p6r-model"
  cp "$build/CMakeCache.txt" "$run/$variant-CMakeCache.txt"
  sha256sum "$build/bin/bench-p6r-model" "$build/src/libllama.so" "$build/ggml/src/"*.so > "$run/$variant-binaries.sha256"
done
if [[ " ${variants[*]} " == *' selected '* ]]; then
  python3 "$repo/reproduction/check_selector_model_paths.py" "$root" "$run/path-check"
fi
python3 "$repo/reproduction/paired_prefill.py" "$root" "$run/paired" "$plan"
echo 'Pinned/paired run completed; physical host CPU exclusivity is not asserted.'
