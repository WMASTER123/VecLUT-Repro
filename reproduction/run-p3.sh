#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
root="${VECLUT_REPRO_DIR:-$repo/.repro}"
mkdir -p "$root";root="$(cd "$root" && pwd)"
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/cache" MPLCONFIGDIR="$root/cache/matplotlib"
export PYTHONPYCACHEPREFIX="$root/cache/pycache" HF_HOME="$root/cache/huggingface" PIP_CACHE_DIR="$root/cache/pip"
export OMP_WAIT_POLICY=PASSIVE OMP_DYNAMIC=FALSE OMP_PROC_BIND=CLOSE
export OMP_PLACES="${P3_OMP_PLACES:-}"
[[ -n "$OMP_PLACES" ]] || export OMP_PLACES='{0},{2},{4},{6}'
mkdir -p "$TMPDIR" "$MPLCONFIGDIR"
for cmd in git cmake c++ python3 make; do command -v "$cmd" >/dev/null || { echo "Missing $cmd";exit 1; };done
args=()
case "${1:-}" in '') ;; --quick) args+=(--quick);; *) echo 'Usage: run-p3.sh [--quick]';exit 2;; esac
run="$root/results/p3-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$run";printf '%s\n' "$run" > "$root/results/latest-p3.txt"
exec > >(tee "$run/session.log") 2>&1
echo "Evidence: $run"
git -C "$repo" rev-parse HEAD > "$run/source-sha.txt"
git -C "$repo" diff --binary > "$run/source.patch"
git -C "$repo" status --short > "$run/git-status.txt"
{ date -Is;uname -srvm;cat /etc/os-release;python3 --version;c++ --version;cmake --version;lscpu;free -b; } > "$run/environment.txt"
python3 "$repo/reproduction/prepare_model_p3.py" "$root" > "$run/model-preparation.log" 2>&1
model="$root/models/falcon3-1b-i2v4/ggml-model-I2_V_4.gguf"
cp "$root/models/falcon3-1b-i2v4/model-manifest.json" "$run/model-manifest.json"
# Reuse P2 build directories: same validated CPU configuration, now also build libllama.
for flavor in normal profile; do
  build="$root/builds/p2-$flavor";enabled=OFF;[[ "$flavor" == normal ]] || enabled=ON
  cmake -S "$repo" -B "$build" -DCMAKE_BUILD_TYPE=Release -DVLUT_PROFILE="$enabled" \
    -DGGML_NATIVE=ON -DGGML_OPENMP=ON -DGGML_CCACHE=OFF -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_METAL=OFF -DGGML_SYCL=OFF \
    -DGGML_BLAS=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_SANITIZE_ADDRESS=OFF -DLLAMA_SANITIZE_UNDEFINED=OFF \
    -DTABLE_ENTRY_SIZE=32 -DWEIGHT_UNROLL_BLOCK=16 -DVLUT_AVX512=OFF -DVLUT_SVE=OFF -DVLUT_ACCELERATE=OFF \
    > "$run/$flavor-configure.log" 2>&1
  cmake --build "$build" --target llama --parallel "${BUILD_JOBS:-4}" > "$run/$flavor-build.log" 2>&1
  bash "$repo/reproduction/compile-p3.sh" "$build"
  key=$(cat "$build/ggml/src/"*.so "$repo/reproduction/test_p1.cpp" | sha256sum | cut -d' ' -f1)
  if [[ ! -f "$build/p1-key.txt" || "$(cat "$build/p1-key.txt")" != "$key" ]]; then
    bash "$repo/reproduction/compile-test.sh" "$build" "$build/bin/test-p1"
    python3 "$repo/reproduction/check_results.py" "$build/bin/test-p1" "$run/$flavor-p1" > "$run/$flavor-p1.log"
    printf '%s\n' "$key" > "$build/p1-key.txt";printf '%s\n' "$run/$flavor-p1" > "$build/p1-evidence.txt"
  fi
  cp "$build/p1-evidence.txt" "$run/$flavor-p1-evidence.txt"
  cp "$build/CMakeCache.txt" "$run/$flavor-CMakeCache.txt"
  sha256sum "$build/bin/bench-p3" "$build/src/libllama.so" "$build/ggml/src/"*.so > "$run/$flavor-binaries.sha256"
done
python3 "$repo/reproduction/run_p3.py" "$root/builds/p2-normal/bin/bench-p3" "$root/builds/p2-profile/bin/bench-p3" "$model" "$run/measurements" "${args[@]}"
python3 "$repo/reproduction/analyze_p3.py" "$run/measurements"
echo 'P3 Falcon3 complete: real generation, verified I2_V_4 calls, uninstrumented prefill/decode.'
