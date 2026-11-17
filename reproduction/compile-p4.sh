#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build="$(realpath "${1:?Pass build directory}")"
out="${2:-$build/bin/test-p4}"
mkdir -p "$(dirname "$out")"
tile=$(sed -n 's/^TABLE_ENTRY_SIZE:STRING=//p' "$build/CMakeCache.txt")
[[ -n "$tile" ]] || { echo 'Missing TABLE_ENTRY_SIZE';exit 1; }
san=()
if grep -q '^LLAMA_SANITIZE_ADDRESS:BOOL=ON' "$build/CMakeCache.txt"; then
  san=(-fsanitize=address,undefined -fno-omit-frame-pointer -g)
fi
"${CXX:-c++}" -std=c++17 -O2 -Wall -Wextra "${san[@]}" -DTABLE_ENTRY_SIZE="$tile" \
  -I"$repo/ggml/include" -I"$repo/ggml/src" "$repo/reproduction/test_p4.cpp" \
  -L"$build/ggml/src" -Wl,-rpath,"$build/ggml/src" -lggml -lggml-cpu -lggml-base -pthread -o "$out"
