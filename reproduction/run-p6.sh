#!/usr/bin/env bash
# Isolated OFF/ON builds; no external comparison frameworks or downloads.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
root="${VECLUT_REPRO_DIR:-$repo/.repro}"
mkdir -p "$root"
root="$(realpath "$root")"
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/cache" PYTHONPYCACHEPREFIX="$root/cache/pycache"
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$root/results"
default_places='{0},{2},{4},{6}'
export OMP_NUM_THREADS=4 OMP_PROC_BIND=close OMP_PLACES="${P6_OMP_PLACES:-$default_places}"
run="$root/results/p6-$(date +%Y%m%d-%H%M%S)-$$"
mkdir "$run"
echo "$run" > "$root/results/latest-p6.txt"
exec > >(tee "$run/session.log") 2>&1
echo "Evidence: $run"
git -C "$repo" rev-parse HEAD > "$run/source-sha.txt"
git -C "$repo" diff --binary > "$run/working-tree.patch"
git -C "$repo" status --short > "$run/git-status.txt"
{ c++ --version; cmake --version; python3 --version; uname -srvm; lscpu; } > "$run/environment.txt"
printf 'OMP_PLACES=%s\nOMP_PROC_BIND=%s\n' "$OMP_PLACES" "$OMP_PROC_BIND" > "$run/affinity.txt"
options=(-DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON -DGGML_CCACHE=OFF
  -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_SYCL=OFF -DGGML_METAL=OFF
  -DGGML_BLAS=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_SERVER=OFF
  -DVLUT_AVX512=OFF -DVLUT_SVE=OFF -DVLUT_ACCELERATE=OFF
  -DVLUT_I2V4_SELECTIVE_WIDEN=OFF -DTABLE_ENTRY_SIZE=32 -DWEIGHT_UNROLL_BLOCK=16)
for variant in off on asan-on profile-off profile-on; do
  build="$root/builds/p6-$variant"
  blocked=OFF; san=OFF; profile=OFF
  [[ "$variant" != *on ]] || blocked=ON
  [[ "$variant" != asan-on ]] || san=ON
  [[ "$variant" != profile-* ]] || profile=ON
  mkdir "$run/$variant"
  cmake -S "$repo" -B "$build" "${options[@]}" -DVLUT_I2V4_BLOCKED_WIDEN="$blocked" \
    -DVLUT_PROFILE="$profile" -DLLAMA_SANITIZE_ADDRESS="$san" -DLLAMA_SANITIZE_UNDEFINED="$san" \
    > "$run/$variant/configure.log" 2>&1
  cmake --build "$build" --target ggml --parallel "${BUILD_JOBS:-4}" > "$run/$variant/build.log" 2>&1
  cp "$build/CMakeCache.txt" "$run/$variant/CMakeCache.txt"
  if [[ "$san" == ON ]]; then
    export ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1
  fi
  bash "$repo/reproduction/compile-test.sh" "$build" "$build/bin/test-p1"
  bash "$repo/reproduction/compile-p4.sh" "$build"
  python3 "$repo/reproduction/check_results.py" "$build/bin/test-p1" "$run/$variant/p1"
  python3 "$repo/reproduction/check_p4.py" "$build/bin/test-p4" "$run/$variant/p4"
  flags=(); [[ "$san" != ON ]] || flags=(-fsanitize=address,undefined -fno-omit-frame-pointer -g)
  c++ -std=c++17 -O2 -Wall -Wextra "${flags[@]}" -I"$repo/ggml/src" \
    "$repo/reproduction/test_widen.cpp" -o "$build/bin/test-widen"
  "$build/bin/test-widen" > "$run/$variant/helper.json"
  unset ASAN_OPTIONS UBSAN_OPTIONS
  if [[ "$san" == OFF ]]; then bash "$repo/reproduction/compile-bench.sh" "$build"; fi
  sha256sum "$build/bin/test-"* "$build/ggml/src/"*.so > "$run/$variant/binaries.sha256"
  if [[ "$san" == OFF ]]; then sha256sum "$build/bin/bench-p2" >> "$run/$variant/binaries.sha256"; fi
  echo "$variant correctness passed"
done
python3 "$repo/reproduction/run_p6.py" "$root" "$run"
python3 "$repo/reproduction/analyze_p6.py" "$run"
echo 'P6 bounded motivation experiment complete. Review net wall time before model tests/default changes.'
