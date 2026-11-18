#ifndef GGML_VLUT_VALID_LANES_H
#define GGML_VLUT_VALID_LANES_H
#include <stdint.h>
// Preserve the author's exact topological dependency order and physical stride.
// Only active token lanes are computed; table row 40 is initialized by the caller.
static inline void vlut_valid_add(int16_t *restrict dst, const int16_t *restrict a,
        const int8_t *restrict b, int valid) {
    for (int lane = 0; lane < valid; ++lane) dst[lane] = a[lane] + b[lane];
}
static inline void vlut_valid_rev(int16_t *restrict dst, const int16_t *restrict a, int valid) {
    for (int lane = 0; lane < valid; ++lane) dst[lane] = -a[lane];
}
static inline void vlut_make_table_i2v_valid(int16_t *restrict table, const int8_t *restrict y, int valid) {
    const int8_t *restrict y0 = y;
    const int8_t *restrict y1 = y0 + TABLE_ENTRY_SIZE;
    const int8_t *restrict y2 = y1 + TABLE_ENTRY_SIZE;
    const int8_t *restrict y3 = y2 + TABLE_ENTRY_SIZE;

    vlut_valid_add(table + 41 * TABLE_ENTRY_SIZE, table + 40 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_add(table + 43 * TABLE_ENTRY_SIZE, table + 40 * TABLE_ENTRY_SIZE, y1, valid);
    vlut_valid_add(table + 49 * TABLE_ENTRY_SIZE, table + 40 * TABLE_ENTRY_SIZE, y2, valid);
    vlut_valid_add(table + 67 * TABLE_ENTRY_SIZE, table + 40 * TABLE_ENTRY_SIZE, y3, valid);
    vlut_valid_rev(table + 39 * TABLE_ENTRY_SIZE, table + 41 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 37 * TABLE_ENTRY_SIZE, table + 43 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 44 * TABLE_ENTRY_SIZE, table + 43 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 31 * TABLE_ENTRY_SIZE, table + 49 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 50 * TABLE_ENTRY_SIZE, table + 49 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_add(table + 52 * TABLE_ENTRY_SIZE, table + 49 * TABLE_ENTRY_SIZE, y1, valid);
    vlut_valid_rev(table + 13 * TABLE_ENTRY_SIZE, table + 67 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 68 * TABLE_ENTRY_SIZE, table + 67 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_add(table + 70 * TABLE_ENTRY_SIZE, table + 67 * TABLE_ENTRY_SIZE, y1, valid);
    vlut_valid_add(table + 76 * TABLE_ENTRY_SIZE, table + 67 * TABLE_ENTRY_SIZE, y2, valid);
    vlut_valid_add(table + 38 * TABLE_ENTRY_SIZE, table + 37 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 36 * TABLE_ENTRY_SIZE, table + 44 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 32 * TABLE_ENTRY_SIZE, table + 31 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_add(table + 34 * TABLE_ENTRY_SIZE, table + 31 * TABLE_ENTRY_SIZE, y1, valid);
    vlut_valid_rev(table + 30 * TABLE_ENTRY_SIZE, table + 50 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 28 * TABLE_ENTRY_SIZE, table + 52 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 53 * TABLE_ENTRY_SIZE, table + 52 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_add(table + 14 * TABLE_ENTRY_SIZE, table + 13 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_add(table + 16 * TABLE_ENTRY_SIZE, table + 13 * TABLE_ENTRY_SIZE, y1, valid);
    vlut_valid_add(table + 22 * TABLE_ENTRY_SIZE, table + 13 * TABLE_ENTRY_SIZE, y2, valid);
    vlut_valid_rev(table + 12 * TABLE_ENTRY_SIZE, table + 68 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 10 * TABLE_ENTRY_SIZE, table + 70 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 71 * TABLE_ENTRY_SIZE, table + 70 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 4 * TABLE_ENTRY_SIZE, table + 76 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 77 * TABLE_ENTRY_SIZE, table + 76 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_add(table + 79 * TABLE_ENTRY_SIZE, table + 76 * TABLE_ENTRY_SIZE, y1, valid);
    vlut_valid_rev(table + 42 * TABLE_ENTRY_SIZE, table + 38 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 48 * TABLE_ENTRY_SIZE, table + 32 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 35 * TABLE_ENTRY_SIZE, table + 34 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 46 * TABLE_ENTRY_SIZE, table + 34 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 29 * TABLE_ENTRY_SIZE, table + 28 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 27 * TABLE_ENTRY_SIZE, table + 53 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 66 * TABLE_ENTRY_SIZE, table + 14 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 17 * TABLE_ENTRY_SIZE, table + 16 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 64 * TABLE_ENTRY_SIZE, table + 16 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 23 * TABLE_ENTRY_SIZE, table + 22 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_add(table + 25 * TABLE_ENTRY_SIZE, table + 22 * TABLE_ENTRY_SIZE, y1, valid);
    vlut_valid_rev(table + 58 * TABLE_ENTRY_SIZE, table + 22 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 11 * TABLE_ENTRY_SIZE, table + 10 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 9 * TABLE_ENTRY_SIZE, table + 71 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 5 * TABLE_ENTRY_SIZE, table + 4 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_add(table + 7 * TABLE_ENTRY_SIZE, table + 4 * TABLE_ENTRY_SIZE, y1, valid);
    vlut_valid_rev(table + 3 * TABLE_ENTRY_SIZE, table + 77 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 1 * TABLE_ENTRY_SIZE, table + 79 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 80 * TABLE_ENTRY_SIZE, table + 79 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 45 * TABLE_ENTRY_SIZE, table + 35 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 47 * TABLE_ENTRY_SIZE, table + 46 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 51 * TABLE_ENTRY_SIZE, table + 29 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 63 * TABLE_ENTRY_SIZE, table + 17 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 65 * TABLE_ENTRY_SIZE, table + 64 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 57 * TABLE_ENTRY_SIZE, table + 23 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 26 * TABLE_ENTRY_SIZE, table + 25 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 55 * TABLE_ENTRY_SIZE, table + 25 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 59 * TABLE_ENTRY_SIZE, table + 58 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_add(table + 61 * TABLE_ENTRY_SIZE, table + 58 * TABLE_ENTRY_SIZE, y1, valid);
    vlut_valid_rev(table + 69 * TABLE_ENTRY_SIZE, table + 11 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 75 * TABLE_ENTRY_SIZE, table + 5 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 8 * TABLE_ENTRY_SIZE, table + 7 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 73 * TABLE_ENTRY_SIZE, table + 7 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 2 * TABLE_ENTRY_SIZE, table + 1 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 0 * TABLE_ENTRY_SIZE, table + 80 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 33 * TABLE_ENTRY_SIZE, table + 47 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 15 * TABLE_ENTRY_SIZE, table + 65 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 54 * TABLE_ENTRY_SIZE, table + 26 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 56 * TABLE_ENTRY_SIZE, table + 55 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 21 * TABLE_ENTRY_SIZE, table + 59 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 19 * TABLE_ENTRY_SIZE, table + 61 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 62 * TABLE_ENTRY_SIZE, table + 61 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 72 * TABLE_ENTRY_SIZE, table + 8 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 74 * TABLE_ENTRY_SIZE, table + 73 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 78 * TABLE_ENTRY_SIZE, table + 2 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 24 * TABLE_ENTRY_SIZE, table + 56 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_add(table + 20 * TABLE_ENTRY_SIZE, table + 19 * TABLE_ENTRY_SIZE, y0, valid);
    vlut_valid_rev(table + 18 * TABLE_ENTRY_SIZE, table + 62 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 6 * TABLE_ENTRY_SIZE, table + 74 * TABLE_ENTRY_SIZE, valid);
    vlut_valid_rev(table + 60 * TABLE_ENTRY_SIZE, table + 20 * TABLE_ENTRY_SIZE, valid);
}

#endif
