#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
root="$(dirname "$repo")"
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/cache" PYTHONPYCACHEPREFIX="$root/cache/pycache"
run="$root/results/profile-$(date +%Y%m%d-%H%M%S)"; mkdir -p "$run"
echo "$run" > "$root/results/latest-profile.txt"
exec > >(tee "$run/session.log") 2>&1
git -C "$repo" rev-parse HEAD > "$run/source-sha.txt"
options=(-DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON -DGGML_CCACHE=OFF -DGGML_OPENMP=ON
 -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_SYCL=OFF -DGGML_METAL=OFF -DGGML_BLAS=OFF
 -DLLAMA_CURL=OFF -DLLAMA_BUILD_SERVER=OFF -DVLUT_AVX512=OFF -DVLUT_SVE=OFF -DVLUT_ACCELERATE=OFF
 -DVLUT_I2V4_BLOCKED_WIDEN=OFF -DVLUT_I2V4_SELECTIVE_WIDEN=ON -DVLUT_PROFILE=ON
 -DVLUT_I2V4_ACCUM_POLICY=safe240 -DTABLE_ENTRY_SIZE=32 -DWEIGHT_UNROLL_BLOCK=16)

for variant in safe240 deferred; do
 build="$root/builds/profile-$variant"; mkdir -p "$run/$variant"
 enabled=OFF; [[ "$variant" != deferred ]] || enabled=ON
 cmake -S "$repo" -B "$build" "${options[@]}" -DVLUT_I2V4_DEFERRED_TRANSPOSE="$enabled" > "$run/$variant/configure.log" 2>&1
 cmake --build "$build" --target ggml --parallel 4 > "$run/$variant/build.log" 2>&1
 bash "$repo/reproduction/compile-bench.sh" "$build"
 cp "$build/CMakeCache.txt" "$run/$variant/CMakeCache.txt"
 sha256sum "$build/ggml/src/"*.so "$build/bin/bench-p2" > "$run/$variant/binaries.sha256"
done
python3 "$repo/reproduction/diagnose_deferred.py" "$root" "$run"
