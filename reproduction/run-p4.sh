#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
root="${VECLUT_REPRO_DIR:-$repo/.repro}"
mkdir -p "$root/results";root="$(realpath "$root")"
export VECLUT_REPRO_DIR="$root" TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/cache" PYTHONPYCACHEPREFIX="$root/cache/pycache"
export OMP_WAIT_POLICY=PASSIVE UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1 ASAN_OPTIONS=detect_leaks=1
args=(--focused)
case "${1:-}" in '') ;; --quick) args=(--quick);; --full) args=();; *) echo 'Usage: run-p4.sh [--quick|--full]';exit 2;; esac
run="$root/results/p4-correctness-$(date +%Y%m%d-%H%M%S)-$$"
mkdir "$run";echo "P4 sanitizer evidence: $run"
printf '%s\n' "$run" > "$root/results/latest-p4-correctness.txt"
git -C "$repo" rev-parse HEAD > "$run/source-sha.txt"
git -C "$repo" diff --binary > "$run/source.patch"
P1_SANITIZE=ON bash "$repo/reproduction/run-p1.sh" > "$run/p1-sanitizer-session.log" 2>&1
cp "$root/results/latest-p1.txt" "$run/p1-evidence.txt"
bash "$repo/reproduction/compile-p4.sh" "$root/builds/asan"
python3 "$repo/reproduction/check_p4.py" "$root/builds/asan/bin/test-p4" "$run/asan-p4" > "$run/asan-p4.log"
cp "$root/builds/asan/CMakeCache.txt" "$run/asan-CMakeCache.txt"
sha256sum "$root/builds/asan/bin/test-p4" "$root/builds/asan/ggml/src/"*.so > "$run/asan-binaries.sha256"
unset ASAN_OPTIONS UBSAN_OPTIONS
bash "$repo/reproduction/run-p3.sh" --model bitnet-3b-i1v2 "${args[@]}"
