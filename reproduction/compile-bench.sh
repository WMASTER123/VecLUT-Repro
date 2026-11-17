#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build="$(realpath "${1:?Build directory}")"
flags=()
if grep -q '^VLUT_PROFILE:BOOL=ON' "$build/CMakeCache.txt"; then flags+=(-DVLUT_PROFILE); fi
tile=$(sed -n 's/^TABLE_ENTRY_SIZE:STRING=//p' "$build/CMakeCache.txt")
mkdir -p "$build/bin"
"${CXX:-c++}" -std=c++17 -O3 -Wall -Wextra -DTABLE_ENTRY_SIZE="$tile" "${flags[@]}" \
  -I"$repo/ggml/include" -I"$repo/ggml/src" "$repo/reproduction/bench_p2.cpp" \
  -L"$build/ggml/src" -Wl,-rpath,"$build/ggml/src" \
  -lggml -lggml-cpu -lggml-base -pthread -o "$build/bin/bench-p2"
