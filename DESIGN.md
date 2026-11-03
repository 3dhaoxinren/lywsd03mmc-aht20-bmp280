# Design

## Compatibility boundary

This is a binary extension for the exact publicly archived Xiaomi LYWSD03MMC
1.0.0_0130 OTA image, SHA256
`d8ca0eb3d660a76d02e33fefa5d8b5186e1f2ccaa91ffb3584486822d18e4340`.
Physical target is the photographed CHMLmini_TLW_V2.0 / HW B2.0 / 202107 board.
No compatibility claim is made for 0159, B1.6, or other thermometer models.

## Driver integration

- New code/rodata at flash address `0x16b00`; no new `.data` or `.bss` allowed by the linker.
- Replace five aligned entry points with 8-byte TC16 literal-load/tail-jump stubs:
  `0xce2c` detection; `0xd0dc` reset; `0xd0fc` init; `0xd154` trigger; `0xd180` poll.
- Reuse the old SHT4x driver's 16-byte state at `0x84728c`; its existing result
  interface reads centi-degrees at `0x847294`, centi-percent humidity at
  `0x847298`, validity at `0x84729a`.
- Sensor dispatch is forced to type 2 at `0x847253`; probing U1 is bypassed.
- Preserve all original image bytes except these five stubs, the header length,
  the former trailing CRC/padding and appended extension. Preserve LCD driver
  selection, native I2C, MiHome BLE/security and Flash settings code.

## New bus

PA6/P8 is SDA; PD7/P7 is SCL. Output latches remain low. Change output-enable
to sink the line or release it, never actively drive high. Enable input/GPIO
mode and internal 10k pulls, preserving unrelated register bits. Bound analog
busy waits and SCL clock stretching. Recover SDA with at most nine clocks;
always attempt STOP and release both pins after transfer failure.

Interrupts remain enabled during bus transfers. Only short analog-register
access is IRQ-serialized. These properties are checked in the instruction
model, not verified electrically; actual timing and radio latency need bench tests.

## Measurements

Asynchronous AHT initialization (20ms) and conversion wait (90ms). Busy status
is bounded by a 500ms timeout, with CRC8 poly 0x31/init 0xff before publishing.
Probe BMP280 ID at 0x76 then 0x77. Use forced temp/pressure x1, filter off,
then sleep. Read calibration on the stack for each sample to avoid allocating
extra retained RAM. BMP temperature/pressure compensation follows Bosch DS001
rev1.26 section3.11.3; reject unusable calibration, invalid raw codes, bad
division and out-of-range outputs. The freestanding 64-bit runtime avoids
dependence on unidentified stock math-helper addresses.

Only commit a new sample when both chips succeed. Clear validity on terminal
failure rather than falsely publishing stale data as a fresh sample. Original
measurement scheduling remains; power consumption and wake/resume behavior
need physical validation.

## Extra telemetry

The original MiHome product has no pressure property. Copy and validate the
native scan-response ADs at `0x845960`, taking length from `0x845959 - 6`.
Append 17 bytes only when every native AD still fits within 31 bytes. Replace
only the exact shape of this extension's previous BTHome AD. Use the stock
`bls_ll_setScanRspData` entry at `0xf2fc`, not direct writes to BLE packet data.
Packet order: packet ID 0x00, signed temperature 0x02, humidity 0x03, pressure
0x04. Pressure in integer Pa equals BTHome 0.01hPa units.

Known privacy tradeoff: the additional measurements are public plaintext even
when the original MiBeacon data are encrypted. No authentication bypass,
key extraction, secret storage or flashing service is added to the firmware.

## OTA and recovery

Body must be 16-byte aligned; header length at 0x18 includes the final four-byte
CRC, hence `length % 16 == 4`. CRC is `zlib.crc32(body) ^ 0xffffffff`.
R1 omitted this alignment; R2 fixes packaging only. Version strings remain
0130 and are not evidence that a device is running the new driver.

The host patcher accepts only the original SHA256. Recovery accepts only its
manifest's patched SHA256 and verifies the restored original hash before writing
a new output file. No scripts here write device Flash, erase settings or accept
credentials. Firmware Flash addresses and BLE APIs are fixed reverse-engineering
findings, not an SDK ABI guarantee.

## Validation model

`tests/test_emulated.py` translates disassembled TC16 instructions into their
Thumb equivalents at unchanged addresses, asserting instruction width. Literal
data are preserved. Unicorn executes the compiled driver, while sensor transfers
and BLE API results are modeled. This does not run the OEM firmware's complete
startup, model TLSR8258 silicon, simulate the radio, or prove MiHome compatibility.
See `docs/validation.md` for physical-user feedback and remaining tests.
