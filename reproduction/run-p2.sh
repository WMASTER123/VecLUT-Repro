#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
root="${VECLUT_REPRO_DIR:-$repo/.repro}"
mkdir -p "$root"; root="$(cd "$root" && pwd)"
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/cache" MPLCONFIGDIR="$root/cache/matplotlib"
export PYTHONPYCACHEPREFIX="$root/cache/pycache"
export OMP_WAIT_POLICY=PASSIVE OMP_DYNAMIC=FALSE OMP_PROC_BIND=CLOSE
# Explicit virtual CPUs; no claim that these map to host P-cores or distinct cores.
# Override for other machines, e.g. P2_OMP_PLACES='{0},{1},{2},{3}'.
export OMP_PLACES="${P2_OMP_PLACES:-}"
[[ -n "$OMP_PLACES" ]] || export OMP_PLACES='{0},{2},{4},{6}'
mkdir -p "$TMPDIR" "$MPLCONFIGDIR"
for cmd in git cmake c++ python3 make; do
  command -v "$cmd" >/dev/null || { echo "Missing $cmd. See reproduction/README.md"; exit 1; }
done
suite=full; target=300
case "${1:-}" in '') ;; --quick) suite=quick;; --confirm) suite=confirm; target=1000;; *) echo 'Usage: run-p2.sh [--quick|--confirm]'; exit 2;; esac
run="$root/results/p2-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$run"; printf '%s\n' "$run" > "$root/results/latest-p2.txt"
exec > >(tee "$run/session.log") 2>&1
echo "Evidence: $run"
git -C "$repo" rev-parse HEAD > "$run/source-sha.txt"
{ date -Is; git -C "$repo" rev-parse HEAD; git -C "$repo" status --short; uname -srvm; cat /etc/os-release; python3 --version; c++ --version; cmake --version; lscpu; free -b; } > "$run/environment.txt"
git -C "$repo" diff --binary > "$run/source.patch"
git -C "$repo" ls-files --others --exclude-standard > "$run/untracked.txt"
if command -v perf >/dev/null; then perf stat -e cycles,instructions true > "$run/perf-check.log" 2>&1 || true; else echo 'perf unavailable' > "$run/perf-check.log"; fi
for flavor in normal profile; do
  build="$root/builds/p2-$flavor"; enabled=OFF; [[ "$flavor" == normal ]] || enabled=ON
  cmake -S "$repo" -B "$build" -DCMAKE_BUILD_TYPE=Release -DVLUT_PROFILE="$enabled" \
    -DGGML_NATIVE=ON -DGGML_CCACHE=OFF -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_METAL=OFF -DGGML_SYCL=OFF \
    -DGGML_OPENMP=ON -DGGML_BLAS=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_SERVER=OFF \
    -DLLAMA_SANITIZE_ADDRESS=OFF -DLLAMA_SANITIZE_UNDEFINED=OFF \
    -DTABLE_ENTRY_SIZE=32 -DWEIGHT_UNROLL_BLOCK=16 -DVLUT_I2V4_BLOCKED_WIDEN=OFF -DVLUT_AVX512=OFF -DVLUT_SVE=OFF -DVLUT_ACCELERATE=OFF \
    > "$run/$flavor-configure.log" 2>&1
  cmake --build "$build" --target ggml --parallel "${BUILD_JOBS:-4}" > "$run/$flavor-build.log" 2>&1
  bash "$repo/reproduction/compile-bench.sh" "$build"
  # Changes to either library or test invalidate cached correctness evidence.
  key=$(cat "$build/ggml/src/"*.so "$repo/reproduction/test_p1.cpp" | sha256sum | cut -d' ' -f1)
  if [[ ! -f "$build/p1-key.txt" || "$(cat "$build/p1-key.txt")" != "$key" ]]; then
    bash "$repo/reproduction/compile-test.sh" "$build" "$build/bin/test-p1"
    python3 "$repo/reproduction/check_results.py" "$build/bin/test-p1" "$run/$flavor-p1" > "$run/$flavor-p1.log"
    printf '%s\n' "$key" > "$build/p1-key.txt"
    printf '%s\n' "$run/$flavor-p1" > "$build/p1-evidence.txt"
  fi
  cp "$build/p1-evidence.txt" "$run/$flavor-p1-evidence.txt"
  cp "$build/CMakeCache.txt" "$run/$flavor-CMakeCache.txt"
  sha256sum "$build/bin/bench-p2" "$build/ggml/src/"*.so > "$run/$flavor-binaries.sha256"
done
# Never compile or execute the two measurement builds concurrently.
python3 "$repo/reproduction/run_p2.py" "$root/builds/p2-normal/bin/bench-p2" "$run/normal" --suite "$suite" --target-ms "$target"
python3 "$repo/reproduction/run_p2.py" "$root/builds/p2-profile/bin/bench-p2" "$run/profile" --suite profile --target-ms 300
python3 "$repo/reproduction/analyze_p2.py" "$run"
echo 'P2 complete: only I2_V_4; profile timings are diagnostic, normal timings are performance results.'
