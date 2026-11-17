#pragma once
// Optional diagnostic instrumentation. Only one graph may be profiled at a time.
// Reset/read only when graph execution is idle. Each worker owns two cache lines.
#ifdef VLUT_PROFILE
#include <stdint.h>
#include <time.h>
struct vlut_profile_record {
    uint64_t alloc_init_ns, build_ns, lookup_ns, widen_ns;
    uint64_t output_ns, free_ns, activation_ns, calls;
    uint64_t clear_ns, padding[7];
};
#ifdef __cplusplus
extern "C" {
#endif
extern struct vlut_profile_record vlut_profile_records[256];
void vlut_profile_reset(void);
#ifdef __cplusplus
}
#endif
static inline uint64_t vlut_profile_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}
#define VLUT_STAMP() uint64_t vlut_tick = vlut_profile_now()
#define VLUT_PHASE(field) do { uint64_t vlut_end = vlut_profile_now(); \
    vlut_profile_records[ith].field += vlut_end - vlut_tick; vlut_tick = vlut_end; } while (0)
#else
#define VLUT_STAMP() ((void)0)
#define VLUT_PHASE(field) ((void)0)
#endif
