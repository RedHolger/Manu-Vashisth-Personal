// Synthetic sensor-frame emitter with seeded fault injection.
// Usage: sim <scenario> <seed> ; prints one hex frame per line to stdout.
// Scenarios: clean | corrupt | drop | reorder | range
// Exit codes: 0 ok. No hardware, no network, no files.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

static uint16_t crc16(const uint8_t* d, size_t n) {
    uint16_t c = 0xFFFF;
    for (size_t i = 0; i < n; ++i) {
        c ^= (uint16_t)d[i] << 8;
        for (int b = 0; b < 8; ++b) c = (c & 0x8000) ? (uint16_t)((c << 1) ^ 0x1021) : (uint16_t)(c << 1);
    }
    return c;
}

// Deterministic PRNG (xorshift32) so streams are reproducible from seed.
struct Rng {
    uint32_t s;
    explicit Rng(uint32_t seed) : s(seed ? seed : 0x9E3779B9u) {}
    uint32_t next() {
        s ^= s << 13; s ^= s >> 17; s ^= s << 5;
        return s;
    }
};

static void emit(const std::vector<uint8_t>& f) {
    for (uint8_t b : f) std::printf("%02X", b);
    std::printf("\n");
}

static std::vector<uint8_t> frame(uint8_t seq, uint8_t type, int16_t value) {
    std::vector<uint8_t> f = {0xA5, 0x5A, seq, type,
                              (uint8_t)((value >> 8) & 0xFF), (uint8_t)(value & 0xFF),
                              0, 0, 0, 0};
    uint16_t c = crc16(f.data(), 10);
    f.insert(f.end(), {(uint8_t)(c >> 8), (uint8_t)(c & 0xFF)});
    return f;
}

int main(int argc, char** argv) {
    if (argc != 3) { std::fprintf(stderr, "usage: sim <scenario> <seed>\n"); return 2; }
    std::string sc = argv[1];
    Rng rng((uint32_t)std::strtoul(argv[2], nullptr, 10));
    const int N = 24;
    std::vector<std::vector<uint8_t>> out;
    for (int i = 0; i < N; ++i) {
        int16_t v = (int16_t)(1000 + (rng.next() % 400) - 200);  // in-range data
        uint8_t t = 0x01;
        if (i % 8 == 7) t = 0x02;  // periodic status frame
        out.push_back(frame((uint8_t)i, t, v));
    }
    if (sc == "corrupt") {
        out[5][7] ^= 0xFF;   // break CRC of frame 5
        out[17][2] ^= 0x40;  // break SYNC-adjacent byte of frame 17
    } else if (sc == "drop") {
        out.erase(out.begin() + 9);
        out.erase(out.begin() + 15);
    } else if (sc == "reorder") {
        std::swap(out[6], out[7]);
    } else if (sc == "range") {
        out[11] = frame(11, 0x01, 9000);  // out-of-range value
    } else if (sc != "clean") {
        std::fprintf(stderr, "unknown scenario\n");
        return 2;
    }
    for (auto& f : out) emit(f);
    return 0;
}
