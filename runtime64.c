/* Minimal freestanding compiler runtime; no dependency on stock libgcc offsets. */
typedef unsigned int u32;
typedef unsigned long long u64;
typedef signed long long s64;
typedef union { u64 v; struct { u32 lo, hi; } w; } wide;
u64 __muldi3(u64 av, u64 bv) {
    wide a, b, r;
    u32 t, lo16, mid, hi;
    a.v = av; b.v = bv;
    t = (a.w.lo & 65535u) * (b.w.lo & 65535u);
    lo16 = t & 65535u;
    t = (a.w.lo >> 16) * (b.w.lo & 65535u) + (t >> 16);
    mid = t & 65535u; hi = t >> 16;
    t = (a.w.lo & 65535u) * (b.w.lo >> 16) + mid;
    r.w.lo = (t << 16) | lo16;
    r.w.hi = hi + (a.w.lo >> 16) * (b.w.lo >> 16) + (t >> 16)
        + a.w.hi * b.w.lo + a.w.lo * b.w.hi;
    return r.v;
}
static u64 divide(u64 n, u64 d) {
    u64 q = 0, r = 0;
    u32 i;
    if (!d) return 0;
    for (i = 0; i < 64; ++i) {
        u32 carry = (u32)(r >> 63);
        r = (r << 1) | (n >> 63);
        n <<= 1; q <<= 1;
        if (carry || r >= d) { r -= d; q |= 1; }
    }
    return q;
}
s64 __divdi3(s64 n, s64 d) {
    u64 a = n < 0 ? -(u64)n : (u64)n;
    u64 b = d < 0 ? -(u64)d : (u64)d;
    u64 q = divide(a, b);
    return (s64)((n < 0) != (d < 0) ? -q : q);
}
