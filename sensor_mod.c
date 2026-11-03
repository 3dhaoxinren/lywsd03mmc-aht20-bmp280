/* LYWSD03MMC B2.0, stock 1.0.0_0130 ONLY. Experimental binary extension.
 * New open-drain software I2C: P8/PA6=SDA, P7/PD7=SCL.
 * No dependency on U1. No writes to Flash, binding data or native I2C/LCD.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed short s16;
typedef signed int s32;
typedef signed long long s64;
typedef unsigned long long u64;
#define R8(a) (*(volatile u8 *)(a))
#define R32(a) (*(volatile u32 *)(a))
#define NOINLINE __attribute__((noinline))
#define TICK R32(0x800740)
#define SDA 0x40
#define SCL 0x80
/* Exactly the 16-byte allocation of the removed SHT4x driver. */
struct sensor_state {
    u32 stamp;
    u8 bmp_addr, state, seq, reserved;
    s32 temp;
    u16 humidity, valid;
};
#define S ((volatile struct sensor_state *)0x84728c)
typedef char size_check[(sizeof(struct sensor_state) == 16) ? 1 : -1];

static u32 elapsed(u32 then) { return TICK - then; }
static void delay_us(u32 us) {
    u32 t = TICK;
    while (elapsed(t) < us * 16u) { }
}
static void sda_low(void) { R8(0x800582) &= (u8)~SDA; }
static void sda_release(void) { R8(0x800582) |= SDA; }
static void scl_low(void) { R8(0x80059a) &= (u8)~SCL; }
static void scl_release(void) { R8(0x80059a) |= SCL; }
static void release_bus(void) { sda_release(); scl_release(); }

/* Analog access is serialized against the stock IRQ handlers, with a timeout. */
static int analog_update(u8 addr, u8 mask, u8 value) {
    u8 irq = R8(0x800643), data;
    u32 t;
    int ok = 0;
    R8(0x800643) = 0;
    R8(0x8000b8) = addr;
    R8(0x8000ba) = 0x40;
    t = TICK;
    while (R8(0x8000ba) & 1) if (elapsed(t) > 1600) goto done;
    data = R8(0x8000b9);
    R8(0x8000ba) = 0;
    R8(0x8000b8) = addr;
    R8(0x8000b9) = (data & (u8)~mask) | value;
    R8(0x8000ba) = 0x60;
    t = TICK;
    while (R8(0x8000ba) & 1) if (elapsed(t) > 1600) goto done;
    ok = 1;
done:
    R8(0x8000ba) = 0;
    R8(0x800643) = irq;
    return ok;
}
NOINLINE int bus_init(void) {
    release_bus();
    R8(0x800583) &= (u8)~SDA;
    R8(0x80059b) &= (u8)~SCL;
    R8(0x800586) |= SDA;
    R8(0x80059e) |= SCL;
    R8(0x800581) |= SDA;
    R8(0x800599) |= SCL;
    /* PM_PIN_PULLUP_10K = 3; preserve every unrelated analog bit. */
    return analog_update(0x0f, 0x30, 0x30) &&
           analog_update(0x15, 0xc0, 0xc0);
}
static int scl_high(void) {
    u32 t;
    scl_release();
    t = TICK;
    while (!(R8(0x800598) & SCL))
        if (elapsed(t) > 16000u) return 0;
    delay_us(5);
    return 1;
}
static int bus_stop(void) {
    int ok;
    scl_low(); sda_low(); delay_us(5);
    ok = scl_high(); sda_release(); delay_us(5);
    release_bus();
    return ok;
}
static int bus_start(void) {
    sda_release();
    if (!scl_high()) return 0;
    if (!(R8(0x800580) & SDA)) return 0;
    sda_low(); delay_us(5); scl_low(); delay_us(5);
    return 1;
}
static int bus_recover(void) {
    int i;
    release_bus();
    if (!scl_high()) return 0;
    if (R8(0x800580) & SDA) return 1;
    for (i = 0; i < 9; ++i) {
        scl_low(); delay_us(5);
        if (!scl_high()) return 0;
    }
    return bus_stop() && (R8(0x800580) & SDA);
}
static int write_byte(u8 b) {
    int i, ack;
    for (i = 0; i < 8; ++i) {
        if (b & 0x80) sda_release(); else sda_low();
        delay_us(5);
        if (!scl_high()) return 0;
        scl_low(); delay_us(5); b <<= 1;
    }
    sda_release(); delay_us(5);
    if (!scl_high()) return 0;
    ack = !(R8(0x800580) & SDA);
    scl_low(); delay_us(5);
    return ack;
}
static int read_byte(u8 *out, int nack) {
    int i;
    u8 b = 0;
    sda_release();
    for (i = 0; i < 8; ++i) {
        delay_us(5);
        if (!scl_high()) return 0;
        b = (b << 1) | !!(R8(0x800580) & SDA);
        scl_low(); delay_us(5);
    }
    if (nack) sda_release(); else sda_low();
    delay_us(5);
    if (!scl_high()) return 0;
    scl_low(); delay_us(5); sda_release(); *out = b;
    return 1;
}
/* This ABI boundary is also the sensor-model interception point in tests. */
NOINLINE int bus_xfer(u32 addr, const u8 *tx, u32 nt, u8 *rx, u32 nr) {
    u32 i;
    int ok = 0;
    if (nt > 32 || nr > 32 || addr > 0x7f) return 0;
    if (!bus_recover() || !bus_start()) goto done;
    if (nt) {
        if (!write_byte((u8)(addr << 1))) goto done;
        for (i = 0; i < nt; ++i) if (!write_byte(tx[i])) goto done;
        if (nr && !bus_start()) goto done;
    }
    if (nr) {
        if (!write_byte((u8)((addr << 1) | 1))) goto done;
        for (i = 0; i < nr; ++i)
            if (!read_byte(rx + i, i + 1 == nr)) goto done;
    }
    ok = 1;
done:
    if (!bus_stop()) ok = 0;
    release_bus();
    return ok;
}
static int read_reg(u8 addr, u8 reg, u8 *buf, u32 n) {
    return bus_xfer(addr, &reg, 1, buf, n);
}
static int write_reg(u8 addr, u8 reg, u8 value) {
    u8 tx[2]; tx[0] = reg; tx[1] = value;
    return bus_xfer(addr, tx, 2, (u8 *)0, 0);
}
NOINLINE u8 aht_crc(const u8 *b, u32 n) {
    u8 c = 0xff;
    u32 i;
    while (n--) {
        c ^= *b++;
        for (i = 0; i < 8; ++i) c = (c & 0x80) ? (c << 1) ^ 0x31 : c << 1;
    }
    return c;
}
static u16 le16(const u8 *p) { return p[0] | ((u16)p[1] << 8); }
/* Fixed-point BMP280 compensation, per Bosch DS001 rev1.26 section3.11.3.
 * Multiplication replaces signed left shifts (which are undefined in C).
 */
NOINLINE int bmp_compensate(const u8 *cal, const u8 *raw, s32 *temp, u32 *pa) {
    s32 at, ap, fine, t;
    s64 x, y, p, z;
    s16 c[12];
    int i;
    for (i = 0; i < 12; ++i) c[i] = (s16)le16(cal + i * 2);
    if (!le16(cal) || le16(cal) == 0xffff ||
        !le16(cal + 6) || le16(cal + 6) == 0xffff) return 0;
    ap = ((u32)raw[0] << 12) | ((u32)raw[1] << 4) | (raw[2] >> 4);
    at = ((u32)raw[3] << 12) | ((u32)raw[4] << 4) | (raw[5] >> 4);
    if (at == 0x80000 || ap == 0x80000) return 0;
    x = ((((s64)at >> 3) - ((s64)le16(cal) * 2)) * c[1]) >> 11;
    z = ((s64)at >> 4) - le16(cal);
    y = (((z * z) >> 12) * c[2]) >> 14;
    /* Bound corrupt calibration before pressure products and narrow casts. */
    if (x + y < -1000000 || x + y > 1000000) return 0;
    fine = (s32)(x + y);
    t = (fine * 5 + 128) >> 8;
    if (t < -4000 || t > 8500) return 0;
    x = (s64)fine - 128000;
    y = x * x * c[8];
    y += x * c[7] * 131072LL;
    y += (s64)c[6] * 34359738368LL;
    x = ((x * x * c[5]) >> 8) + x * c[4] * 4096LL;
    x += 1LL << 47;
    if (x <= 0 || x > 9223372036854775807LL / le16(cal + 6)) return 0;
    x = (x * le16(cal + 6)) >> 33;
    if (x <= 0) return 0;
    p = 1048576 - ap;
    z = p * 2147483648LL - y;
    /* Prevent overflow of z*3125 on invalid trimming bytes. */
    if (z < 0 || z > 2951479051793528LL) return 0;
    p = (z * 3125) / x;
    if (p < 0 || p > 100000000000LL) return 0;
    x = ((s64)c[11] * (p >> 13) * (p >> 13)) >> 25;
    y = ((s64)c[10] * p) >> 19;
    p = ((p + x + y) >> 8) + (s64)c[9] * 16;
    p = (p + 128) >> 8;
    if (p < 30000 || p > 110000) return 0;
    *temp = t; *pa = (u32)p;
    return 1;
}
/* Add telemetry only if all native scan-response ADs still fit, never truncate.
 * Stock MiHome has no pressure property; BTHome is an extra scan-response AD.
 */
NOINLINE int pressure_scan(s32 t, u32 h, u32 pa, u32 seq) {
    u8 out[31];
    const volatile u8 *old = (volatile u8 *)0x845960;
    u32 rf = R8(0x845959), n, i = 0, j = 0, k, len;
    if (rf < 6 || rf > 37) return 0;
    n = rf - 6;
    while (i < n) {
        len = old[i];
        if (!len || i + len + 1 > n) return 0;
        if (!(len == 16 && old[i+1] == 0x16 && old[i+2] == 0xd2 &&
              old[i+3] == 0xfc && old[i+4] == 0x40 && old[i+5] == 0 &&
              old[i+7] == 2 && old[i+10] == 3 && old[i+13] == 4)) {
            for (k = 0; k <= len; ++k) out[j++] = old[i+k];
        }
        i += len + 1;
    }
    if (j + 17 > 31) return 0;
    out[j++] = 16; out[j++] = 0x16; out[j++] = 0xd2; out[j++] = 0xfc;
    out[j++] = 0x40; out[j++] = 0; out[j++] = seq;
    out[j++] = 2; out[j++] = (u8)t; out[j++] = (u8)(t >> 8);
    out[j++] = 3; out[j++] = (u8)h; out[j++] = (u8)(h >> 8);
    out[j++] = 4; out[j++] = (u8)pa; out[j++] = (u8)(pa >> 8); out[j++] = (u8)(pa >> 16);
    return ((int (*)(const u8 *, u8))0xf2fd)(out, (u8)j) == 0;
}
static int fail_sample(void) {
    S->state = 0; S->stamp = 0; S->valid = 0;
    release_bus();
    return 0;
}
NOINLINE int mod_detect(void) {
    R8(0x847253) = 2;
    return 1;
}
NOINLINE int mod_init(void) {
    S->stamp = 0; S->bmp_addr = 0; S->state = 0;
    S->seq = 0; S->reserved = 0; S->temp = 0;
    S->humidity = 0; S->valid = 0;
    bus_init();
    return 0;
}
static int begin_measure(void) {
    u8 tx[3], id, status, addr;
    addr = 0x76;
    if (!read_reg(addr, 0xd0, &id, 1) || id != 0x58) {
        addr = 0x77;
        if (!read_reg(addr, 0xd0, &id, 1) || id != 0x58) return fail_sample();
    }
    if (!read_reg(addr, 0xf3, &status, 1) || (status & 9)) return fail_sample();
    if (!write_reg(addr, 0xf5, 0) || !write_reg(addr, 0xf4, 0x25)) return fail_sample();
    tx[0] = 0xac; tx[1] = 0x33; tx[2] = 0;
    if (!bus_xfer(0x38, tx, 3, (u8 *)0, 0)) return fail_sample();
    S->bmp_addr = addr;
    S->stamp = TICK;
    S->state = 1;
    return 1;
}
NOINLINE void mod_start(void) {
    u8 status, tx[3];
    if (S->state) {
        if (elapsed(S->stamp) < 8000000u) return;
        fail_sample();
    }
    if (!bus_init() || !bus_xfer(0x38, (u8 *)0, 0, &status, 1)) {
        fail_sample(); return;
    }
    if (status & 0x80) { fail_sample(); return; }
    if (!(status & 8)) {
        tx[0] = 0xbe; tx[1] = 8; tx[2] = 0;
        if (!bus_xfer(0x38, tx, 3, (u8 *)0, 0)) { fail_sample(); return; }
        S->stamp = TICK; S->state = 2;
        return;
    }
    begin_measure();
}
NOINLINE int mod_poll(void) {
    u8 aht[7], cal[24], raw[6], status;
    s32 temp;
    u32 pa, h, age;
    if (!S->state) return 0;
    age = elapsed(S->stamp);
    if (age > 8000000u) return fail_sample();
    if (S->state == 2) {
        if (age < 320000u) return 2;
        if (!bus_init() || !bus_xfer(0x38, (u8 *)0, 0, &status, 1) ||
            (status & 0x88) != 8) return fail_sample();
        return begin_measure() ? 2 : 0;
    }
    if (age < 1440000u) return 2;
    if (!bus_init() || !bus_xfer(0x38, (u8 *)0, 0, aht, 7)) return fail_sample();
    if (aht[0] & 0x80) return 2;
    if (!(aht[0] & 8) || aht_crc(aht, 6) != aht[6]) return fail_sample();
    if (!read_reg(S->bmp_addr, 0xf3, &status, 1)) return fail_sample();
    if (status & 9) return 2;
    if (!read_reg(S->bmp_addr, 0x88, cal, 24) ||
        !read_reg(S->bmp_addr, 0xf7, raw, 6) ||
        !bmp_compensate(cal, raw, &temp, &pa)) return fail_sample();
    h = ((u32)aht[1] << 12) | ((u32)aht[2] << 4) | (aht[3] >> 4);
    h = (u32)(((u64)h * 10000u + 524288u) >> 20);
    if (h > 10000) return fail_sample();
    S->temp = temp; S->humidity = (u16)h; S->valid = 1;
    S->state = 0; S->stamp = 0; S->seq++;
    pressure_scan(temp, h, pa, S->seq);
    return 1;
}
