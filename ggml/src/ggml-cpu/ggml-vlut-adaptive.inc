// Included only inside ggml_gemm_i2v4_i8v_lut's experimental branch.
// For ternary weights, every intermediate partial sum is bounded by sum(abs(a)).
// Include padded lanes too, so unused SIMD lanes also remain representable.
{
    const int group_size = 16; // MAKE_TABLES_I2S_BLOCK4 address unit, not flush interval.
    const int i = 0;
    const int tiles = nr / TABLE_ENTRY_SIZE + (nr % TABLE_ENTRY_SIZE != 0);
    for (int t = 0; t < tiles; ++t) {
        const int valid = nr - t * TABLE_ENTRY_SIZE < TABLE_ENTRY_SIZE ? nr - t * TABLE_ENTRY_SIZE : TABLE_ENTRY_SIZE;
        const int8_t *restrict y_block = (const int8_t *) vy + (size_t)t * n * TABLE_ENTRY_SIZE;
        int bounds[TABLE_ENTRY_SIZE] = {0};
        for (int g = 0; g < n / 16; ++g) {
            int atom[TABLE_ENTRY_SIZE] = {0};
            for (int k = 0; k < 16; ++k) {
                const int8_t *a = y_block + (size_t)(g * 16 + k) * TABLE_ENTRY_SIZE;
                for (int lane = 0; lane < TABLE_ENTRY_SIZE; ++lane) {
                    const int value = a[lane]; // promote before negating -128
                    atom[lane] += value < 0 ? -value : value;
                }
            }
            int flush = 0;
            for (int lane = 0; lane < TABLE_ENTRY_SIZE; ++lane)
                flush |= bounds[lane] + atom[lane] > INT16_MAX;
            VLUT_PHASE(build_ns); // includes bound calculation; never hidden from wall time
            if (flush) {
                ACCUMULATE_I2V4_TRANS(sum_i16, sum_i32, nc, valid, t);
                VLUT_PHASE(widen_ns);
                memset(sum_i16, 0, sizeof(int16_t) * TABLE_ENTRY_SIZE * nc);
                memset(bounds, 0, sizeof(bounds));
                VLUT_PHASE(clear_ns);
            }
            for (int lane = 0; lane < TABLE_ENTRY_SIZE; ++lane) bounds[lane] += atom[lane];
            MAKE_TABLES_I2S_BLOCK4(g);
            VLUT_PHASE(build_ns);
            const uint8_t *restrict x_block = (const uint8_t *)vx + (size_t)g * 4 * bs;
            ADD_TABLE_ENTRIES_BLOCK4(nc);
            VLUT_PHASE(lookup_ns);
        }
        ACCUMULATE_I2V4_TRANS(sum_i16, sum_i32, nc, valid, t);
        VLUT_PHASE(widen_ns);
        memset(sum_i16, 0, sizeof(int16_t) * TABLE_ENTRY_SIZE * nc);
        VLUT_PHASE(clear_ns);
    }
}
