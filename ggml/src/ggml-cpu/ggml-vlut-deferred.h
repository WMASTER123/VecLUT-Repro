#ifndef GGML_VLUT_DEFERRED_H
#define GGML_VLUT_DEFERRED_H

#include <stddef.h>
#include <stdint.h>

// INT16 source: [row][width]. INT32 destination: [row][valid].
// Tail tiles are compact, so no padding or extra accumulator allocation is needed.
static inline void vlut_i2v4_contiguous_widen(const int16_t * restrict src,
        int32_t * restrict dst, int rows, int valid, int width) {
    if (valid == width) {
        const size_t count = (size_t) rows * width;
        for (size_t i = 0; i < count; ++i) {
            dst[i] += (int32_t) src[i];
        }
    } else {
        for (int row = 0; row < rows; ++row) {
            for (int lane = 0; lane < valid; ++lane) {
                dst[(size_t) row * valid + lane] += src[(size_t) row * width + lane];
            }
        }
    }
}

#endif
