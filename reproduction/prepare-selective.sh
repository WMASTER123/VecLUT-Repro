#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
root="$(realpath "${VECLUT_REPRO_DIR:-$repo/.repro}")"
run="${1:-$root/results/p6-selective-build-$(date +%Y%m%d-%H%M%S)-$$}"
mkdir -p "$run"
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/cache" PYTHONPYCACHEPREFIX="$root/cache/pycache"
export OMP_WAIT_POLICY=PASSIVE OMP_DYNAMIC=FALSE OMP_PROC_BIND=CLOSE OMP_PLACES='{0},{2},{4},{6}'
exec > >(tee "$run/session.log") 2>&1
echo "Evidence: $run"
git -C "$repo" rev-parse HEAD > "$run/source-sha.txt"
git -C "$repo" diff --binary > "$run/source.patch"
options=(-DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON -DGGML_CCACHE=OFF -DGGML_OPENMP=ON
  -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_SYCL=OFF -DGGML_METAL=OFF
  -DGGML_BLAS=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_SERVER=OFF
  -DVLUT_AVX512=OFF -DVLUT_SVE=OFF -DVLUT_ACCELERATE=OFF
  -DVLUT_I2V4_BLOCKED_WIDEN=OFF -DTABLE_ENTRY_SIZE=32 -DWEIGHT_UNROLL_BLOCK=16)
for variant in off selected selected-profile selected-asan; do
  build="$root/builds/p6-$variant"
  selective=ON; san=OFF; profile=OFF; target=llama
  [[ "$variant" != off ]] || selective=OFF
  [[ "$variant" != selected-profile ]] || profile=ON
  if [[ "$variant" == selected-asan ]]; then san=ON; target=ggml; fi
  mkdir -p "$run/$variant"
  cmake -S "$repo" -B "$build" "${options[@]}" -DVLUT_I2V4_SELECTIVE_WIDEN="$selective" \
    -DVLUT_PROFILE="$profile" -DLLAMA_SANITIZE_ADDRESS="$san" -DLLAMA_SANITIZE_UNDEFINED="$san" \
    > "$run/$variant/configure.log" 2>&1
  cmake --build "$build" --target "$target" --parallel "${BUILD_JOBS:-4}" > "$run/$variant/build.log" 2>&1
  cp "$build/CMakeCache.txt" "$run/$variant/CMakeCache.txt"
  if [[ "$san" == ON ]]; then export ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1; fi
  bash "$repo/reproduction/compile-test.sh" "$build" "$build/bin/test-p1"
  bash "$repo/reproduction/compile-p4.sh" "$build"
  python3 "$repo/reproduction/check_results.py" "$build/bin/test-p1" "$run/$variant/p1" > "$run/$variant/p1.log"
  python3 "$repo/reproduction/check_p4.py" "$build/bin/test-p4" "$run/$variant/p4" > "$run/$variant/p4.log"
  "$build/bin/test-p1" --selective-boundaries > "$run/$variant/selective-boundaries.log" 2>&1
  grep -q $'SUMMARY\tchecks=8\tfailures=0' "$run/$variant/selective-boundaries.log"
  flags=(); [[ "$san" != ON ]] || flags=(-fsanitize=address,undefined -fno-omit-frame-pointer -g)
  c++ -std=c++17 -O2 -Wall -Wextra "${flags[@]}" -I"$repo/ggml/src" \
    "$repo/reproduction/test_widen.cpp" -o "$build/bin/test-widen"
  "$build/bin/test-widen" > "$run/$variant/helper.json"
  unset ASAN_OPTIONS UBSAN_OPTIONS
  if [[ "$san" == OFF ]]; then
    bash "$repo/reproduction/compile-p3.sh" "$build" "$build/bin/bench-p6r-model"
    bash "$repo/reproduction/compile-bench.sh" "$build"
  fi
  sha256sum "$build/bin/test-"* "$build/ggml/src/"*.so > "$run/$variant/binaries.sha256"
  if [[ "$san" == OFF ]]; then sha256sum "$build/bin/bench-p6r-model" "$build/bin/bench-p2" "$build/src/libllama.so" >> "$run/$variant/binaries.sha256"; fi
  echo "$variant: P1/P4, 8 selector graph boundaries, 180 helper/10 policy checks passed"
done
