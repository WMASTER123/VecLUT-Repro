// Independent coordinate oracle for the actual production helper.
#include "ggml-cpu/ggml-vlut-widen.h"
#include <array>
#include <iostream>
#include <stdexcept>
#include <vector>

int main() try {
    size_t cases = 0;
    for (size_t rows : {1, 3, 5, 15, 16, 17, 31, 32, 81}) {
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
    std::cout << "{\"passed\":true,\"cases\":" << cases << "}\n";
} catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
}
