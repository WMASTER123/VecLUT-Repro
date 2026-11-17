// Independent coordinate oracle for the actual production helper.
#include "ggml-cpu/ggml-vlut-widen.h"
#include <array>
#include <iostream>
#include <stdexcept>
#include <vector>

int main() try {
    struct policy_case { size_t rows, k, tokens; int threads; size_t tile; bool expected; };
    const policy_case policies[] = {
        {2560,3072,32,1,32,true}, {2559,3072,32,1,32,false},
        {2560,3056,32,1,32,false}, {2560,3072,31,1,32,false},
        {2560,3072,33,1,32,true}, {8640,3200,128,1,32,true},
        {8192,2048,128,1,32,false}, {3200,8640,128,2,32,false},
        {3200,3200,128,4,32,false}, {3200,3200,128,1,16,false}
    };
    for (const auto &p : policies) {
        if (bool(vlut_i2v4_select_widen(p.rows,p.k,p.tokens,p.threads,p.tile)) != p.expected)
            throw std::runtime_error("selector boundary mismatch");
    }
    size_t cases = 0;
    for (size_t rows : {1, 3, 5, 15, 16, 17, 31, 32, 81, 2559, 2560, 2561}) {
        for (size_t tokens : {1, 8, 16, 31, 32}) {
            for (int pattern = 0; pattern < 3; ++pattern) {
                std::vector<int16_t> src(rows * 32 + 2, 12345);
                const std::array<int16_t, 5> values = {-32768, 32767, -1, 0, 1};
                for (size_t k = 0; k < rows * 32; ++k) {
                    src[k + 1] = pattern == 0 ? -32768 : pattern == 1 ? 32767 : values[k % values.size()];
                }
                const auto saved = src;
                std::vector<int32_t> dst(rows * 32 + 2, 1234567);
                const auto initial = dst;
                vlut_i2v4_blocked_widen(src.data() + 1, dst.data() + 1, rows, tokens, 32);
                for (size_t k = 0; k < dst.size(); ++k) {
                    int64_t expected = initial[k];
                    if (k > 0 && k <= rows * tokens) {
                        const size_t coordinate = k - 1;
                        expected += saved[1 + (coordinate % rows) * 32 + coordinate / rows];
                    }
                    if (dst[k] != expected) throw std::runtime_error("coordinate/canary mismatch");
                }
                if (src != saved) throw std::runtime_error("source was modified");
                ++cases;
            }
        }
    }
    std::cout << "{\"passed\":true,\"cases\":" << cases << ",\"policy_cases\":10}\n";
} catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
}
