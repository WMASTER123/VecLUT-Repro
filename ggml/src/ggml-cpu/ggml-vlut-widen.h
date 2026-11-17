#pragma once

#include <stddef.h>
#include <stdint.h>

// Only I2_V_4 uses this experimental path. src is [rows][tile_size], while
// dst points to one [valid_tokens][rows] tile in the persistent INT32 sum.
// The caller guarantees that each addition is representable in INT32.
// Clearing src remains a separate operation with unchanged timing/semantics.
static inline void vlut_i2v4_blocked_widen(const int16_t * src, int32_t * dst,
                                         size_t rows, size_t valid_tokens,
                                         size_t tile_size) {
    const size_t block_rows = 16;
    for (size_t begin = 0; begin < rows; begin += block_rows) {
        const size_t end = rows - begin < block_rows ? rows : begin + block_rows;
        for (size_t token = 0; token < valid_tokens; ++token) {
            for (size_t row = begin; row < end; ++row) {
                dst[token * rows + row] += (int32_t) src[row * tile_size + token];
            }
        }
    }
}
