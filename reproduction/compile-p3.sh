#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build="$(realpath "${1:?Build directory}")"
flags=()
if grep -q '^VLUT_PROFILE:BOOL=ON' "$build/CMakeCache.txt"; then flags+=(-DVLUT_PROFILE); fi
mkdir -p "$build/bin"
"${CXX:-c++}" -std=c++17 -O3 -Wall -Wextra "${flags[@]}" \
  -I"$repo/include" -I"$repo/common" -I"$repo/ggml/include" -I"$repo/ggml/src" \
  "$repo/reproduction/bench_p3.cpp" -L"$build/src" -L"$build/ggml/src" \
  -Wl,-rpath,"$build/src:$build/ggml/src" -lllama -lggml -lggml-cpu -lggml-base -pthread -o "$build/bin/bench-p3"
