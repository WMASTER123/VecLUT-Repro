#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; root="$(dirname "$repo")"
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/cache" PYTHONPYCACHEPREFIX="$root/cache/pycache"
run="$root/results/lane-build-$(date +%Y%m%d-%H%M%S)"; mkdir -p "$run"
echo "$run" > "$root/results/latest-lane-build.txt"
exec > >(tee "$run/session.log") 2>&1
git -C "$repo" rev-parse HEAD > "$run/source-sha.txt"
git -C "$repo" diff --binary > "$run/source.patch"
export OMP_WAIT_POLICY=PASSIVE OMP_DYNAMIC=FALSE OMP_PROC_BIND=CLOSE OMP_PLACES='{0},{2},{4},{6}'
options=(-DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON -DGGML_CCACHE=OFF -DGGML_OPENMP=ON
 -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_SYCL=OFF -DGGML_METAL=OFF -DGGML_BLAS=OFF
 -DLLAMA_CURL=OFF -DLLAMA_BUILD_SERVER=OFF -DVLUT_AVX512=OFF -DVLUT_SVE=OFF -DVLUT_ACCELERATE=OFF
 -DVLUT_I2V4_BLOCKED_WIDEN=OFF -DVLUT_I2V4_SELECTIVE_WIDEN=ON -DVLUT_PROFILE=OFF
 -DVLUT_I2V4_ACCUM_POLICY=safe240 -DTABLE_ENTRY_SIZE=32 -DWEIGHT_UNROLL_BLOCK=16)

for variant in valid valid-asan; do
 build="$root/builds/p6-$variant"; mkdir -p "$run/$variant"
 san=OFF; target=llama
 if [[ "$variant" == valid-asan ]]; then san=ON; target=ggml; fi
 cmake -S "$repo" -B "$build" "${options[@]}" -DVLUT_I2V4_DEFERRED_TRANSPOSE=ON -DVLUT_I2V4_VALID_LANES=ON -DLLAMA_SANITIZE_ADDRESS="$san" -DLLAMA_SANITIZE_UNDEFINED="$san" > "$run/$variant/configure.log" 2>&1
 cmake --build "$build" --target "$target" --parallel 4 > "$run/$variant/build.log" 2>&1
 cp "$build/CMakeCache.txt" "$run/$variant/CMakeCache.txt"
 bash "$repo/reproduction/compile-test.sh" "$build" "$run/$variant/test-p1"
 if [[ "$san" == ON ]]; then export ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1; fi
 python3 "$repo/reproduction/check_results.py" "$run/$variant/test-p1" "$run/$variant/p1" > "$run/$variant/p1.log"
 "$run/$variant/test-p1" --accum-boundaries > "$run/$variant/accum-boundaries.log" 2>&1
 "$run/$variant/test-p1" --valid-lanes > "$run/$variant/valid-lanes.log" 2>&1
 bash "$repo/reproduction/compile-p4.sh" "$build"
 python3 "$repo/reproduction/check_p4.py" "$build/bin/test-p4" "$run/$variant/p4" > "$run/$variant/p4.log"
 if [[ "$san" == OFF ]]; then
  bash "$repo/reproduction/compile-p3.sh" "$build" "$build/bin/bench-p6r-model"
  bash "$repo/reproduction/compile-bench.sh" "$build"
 fi
 unset ASAN_OPTIONS UBSAN_OPTIONS
 sha256sum "$build/ggml/src/"*.so "$run/$variant/test-p1" > "$run/$variant/binaries.sha256"
 echo "$variant passed"
done
# New boundary tests also run against the unchanged current candidate.
bash "$repo/reproduction/compile-test.sh" "$root/builds/p6-deferred" "$run/test-reference"
"$run/test-reference" --valid-lanes > "$run/reference-valid-lanes.log" 2>&1
