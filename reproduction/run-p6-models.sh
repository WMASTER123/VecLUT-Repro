#!/usr/bin/env bash
# Optional whole-model confirmation after the P6 kernel motivation gate.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
root="$(realpath "${VECLUT_REPRO_DIR:-$repo/.repro}")"
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/cache" PYTHONPYCACHEPREFIX="$root/cache/pycache"
export OMP_WAIT_POLICY=PASSIVE OMP_DYNAMIC=FALSE OMP_PROC_BIND=CLOSE
export OMP_PLACES="${P6_OMP_PLACES:-}"
[[ -n "$OMP_PLACES" ]] || export OMP_PLACES='{0},{2},{4},{6}'
for flag in P3_AUDIT_LOGITS P3_AUDIT_NODES P3_AUDIT_STEP; do
  [[ -z "${!flag:-}" ]] || { echo "Unset diagnostic $flag before timing"; exit 1; }
done
run="$root/results/p6-models-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$run"
echo "$run" > "$root/results/latest-p6-models.txt"
exec > >(tee "$run/session.log") 2>&1
echo "Evidence: $run"
git -C "$repo" rev-parse HEAD > "$run/source-sha.txt"
git -C "$repo" diff --binary > "$run/source.patch"
git -C "$repo" status --short > "$run/git-status.txt"
{ uname -srvm; c++ --version; lscpu; } > "$run/environment.txt"
for variant in off on; do
  build="$root/builds/p6-$variant"
  flag=OFF;[[ "$variant" == off ]] || flag=ON
  for setting in "VLUT_I2V4_BLOCKED_WIDEN:BOOL=$flag" 'VLUT_PROFILE:BOOL=OFF' \
                 'CMAKE_BUILD_TYPE:STRING=Release' 'LLAMA_SANITIZE_ADDRESS:BOOL=OFF'; do
    grep -qx "$setting" "$build/CMakeCache.txt" || { echo 'Run P6 kernel preparation first'; exit 1; }
  done
  cmake --build "$build" --target llama --parallel "${BUILD_JOBS:-4}" > "$run/$variant-build.log" 2>&1
  bash "$repo/reproduction/compile-test.sh" "$build" "$build/bin/test-p1"
  python3 "$repo/reproduction/check_results.py" "$build/bin/test-p1" "$run/$variant-p1" > "$run/$variant-p1.log"
  bash "$repo/reproduction/compile-p3.sh" "$build"
  cp "$build/CMakeCache.txt" "$run/$variant-CMakeCache.txt"
  sha256sum "$build/bin/bench-p3" "$build/src/libllama.so" "$build/ggml/src/"*.so > "$run/$variant-binaries.sha256"
done
for model in falcon3-1b-i2v4 bitnet-3b-i2v4; do
  python3 "$repo/reproduction/prepare_model_p3.py" "$root" "$model" > "$run/$model-verification.log"
  cp "$root/models/$model/model-manifest.json" "$run/$model-manifest.json"
done
python3 "$repo/reproduction/run_p6_models.py" "$root" "$run"
echo 'P6 model OFF/ON confirmation completed; inspect both batches and regressions.'
