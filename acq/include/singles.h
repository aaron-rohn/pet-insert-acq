#ifndef SINGLES_H
#define SINGLES_H

#include <cinttypes>
#include <iostream>
#include <cstring>
#include <vector>
#include <deque>
#include <fstream>
#include <atomic>

namespace Record
{
    const int event_size = 16;
    const int nmodules = 16;

    inline bool is_header(uint8_t b)
    { return (b >> 3) == 0x1F; };

    inline bool is_single(uint8_t d[])
    { return d[0] & 0x4; };

    inline uint8_t get_block(uint8_t d[])
    { return ((d[0] << 4) | (d[1] >> 4)) & 0x3F; };

    inline uint8_t get_module(uint8_t d[])
    { return ((d[0] << 2) | (d[1] >> 6)) & 0xF; };

    inline void read(std::ifstream &f, uint8_t d[], size_t n = event_size)
    { f.read((char*)d, n); };

    void align(std::ifstream&, uint8_t[]);
    bool go_to_tt(std::ifstream&, uint64_t, std::atomic_bool&);
};

struct TimeTag {
    //const static uint64_t clks_per_tt = 0xFFFFF;
    const static uint64_t clks_per_tt = 800'000;

    uint8_t mod;
    uint64_t value;
    TimeTag(uint8_t[]);
    TimeTag(): mod(0), value(0) {};
};

struct Single {
    static const int nch = 8;
    static const int nblocks = 64;

    uint16_t energies[nch] = {0};
    uint8_t blk, mod;
    uint64_t time, abs_time;
    Single(uint8_t[], const TimeTag&);

    inline bool operator<(const Single &rhs) const
    { return abs_time < rhs.abs_time; }
};

#endif
