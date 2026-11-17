#!/usr/bin/env bash
# Run from any directory. Linux / existing WSL; no model or Python package download.
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
root="${VECLUT_REPRO_DIR:-$repo/.repro}"
mkdir -p "$root"
root="$(cd "$root" && pwd)"
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/cache"
export HF_HOME="$root/cache/huggingface" PIP_CACHE_DIR="$root/cache/pip"
export PYTHONPYCACHEPREFIX="$root/cache/pycache"
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME"
for cmd in git cmake c++ python3 make; do
  command -v "$cmd" >/dev/null || { echo "Missing $cmd. See reproduction/README.md"; exit 1; }
done
[[ ${1:-} == '' || ${1:-} == '--with-baseline' ]] || { echo 'Usage: bash reproduction/run-p1.sh [--with-baseline]'; exit 2; }
run="$root/results/p1-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$run"
printf '%s\n' "$run" > "$root/results/latest-p1.txt"
exec > >(tee "$run/session.log") 2>&1
echo "Evidence: $run"
git -C "$repo" rev-parse HEAD > "$run/source-sha.txt"
git -C "$repo" diff --binary > "$run/working-tree.patch"
git -C "$repo" status --short > "$run/git-status.txt"
{ c++ --version; cmake --version; python3 --version; uname -srvm; } > "$run/environment.txt"
san="${P1_SANITIZE:-OFF}"
if [[ "$san" != OFF ]]; then
  export UBSAN_OPTIONS="${UBSAN_OPTIONS:-halt_on_error=1:print_stacktrace=1}"
  export ASAN_OPTIONS="${ASAN_OPTIONS:-detect_leaks=1}"
fi
suffix=dev
[[ "$san" == OFF ]] || suffix=asan
build="$root/builds/$suffix"
options=(-DCMAKE_BUILD_TYPE=RelWithDebInfo -DGGML_NATIVE=ON -DGGML_CCACHE=OFF
  -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_SYCL=OFF -DGGML_METAL=OFF
  -DGGML_BLAS=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_SERVER=OFF
  -DVLUT_AVX512=OFF -DVLUT_SVE=OFF -DVLUT_ACCELERATE=OFF
  -DTABLE_ENTRY_SIZE=32 -DWEIGHT_UNROLL_BLOCK=16)
cmake -S "$repo" -B "$build" "${options[@]}" \
  -DLLAMA_SANITIZE_ADDRESS="$san" -DLLAMA_SANITIZE_UNDEFINED="$san" 2>&1 | tee "$run/configure.log"
cmake --build "$build" --target ggml --parallel "${BUILD_JOBS:-4}" 2>&1 | tee "$run/build.log"
bash "$repo/reproduction/compile-test.sh" "$build" "$build/bin/test-p1"
cp "$build/CMakeCache.txt" "$run/CMakeCache.txt"
sha256sum "$build/bin/test-p1" "$build/ggml/src/"*.so > "$run/binaries.sha256"
python3 "$repo/reproduction/check_results.py" "$build/bin/test-p1" "$run/fixed"
if [[ ${1:-} == '--with-baseline' ]]; then
  baseline=7a813d9c2b6c73d1066eeff49b67794318f682bd
  orig="$root/author-source"
  if [[ ! -e "$orig" ]]; then git -C "$repo" worktree add --detach "$orig" "$baseline"; fi
  [[ "$(git -C "$orig" rev-parse HEAD)" == "$baseline" ]] || { echo 'Unexpected author SHA'; exit 1; }
  [[ -z "$(git -C "$orig" status --porcelain)" ]] || { echo 'Author worktree is modified'; exit 1; }
  original_build="$root/builds/author-p1"
  cmake -S "$orig" -B "$original_build" "${options[@]}" 2>&1 | tee "$run/author-configure.log"
  cmake --build "$original_build" --target ggml --parallel "${BUILD_JOBS:-4}" 2>&1 | tee "$run/author-build.log"
  bash "$repo/reproduction/compile-test.sh" "$original_build" "$original_build/bin/test-p1"
  python3 "$repo/reproduction/check_results.py" "$original_build/bin/test-p1" "$run/author" --baseline
fi
echo 'P1 completed. This is correctness validation, not a performance result.'
