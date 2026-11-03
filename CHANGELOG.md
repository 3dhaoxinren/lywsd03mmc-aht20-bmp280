# Changelog

## R2 — 2026-11-03

- Open-source snapshot of the PA6/P8 SDA + PD7/P7 SCL AHT20/BMP280 driver extension.
- Preserve stock 0130 MiHome protocol path, select BMP temperature/AHT humidity,
  and opportunistically add BTHome pressure scan-response data.
- Fix R1 packaging: align the body to 16 bytes, then update header length and CRC.
  Final image is 96436 bytes; executable driver bytes are unchanged from R1.
- Add exact-original input guard, restore verification, TC16 instruction-equivalent
  tests, actual flasher-parser tests, and explicit user-feedback/untested boundaries.
- Do not redistribute full OEM or modified OEM images, credentials or screenshots.

## R1 — not for flashing

The initial locally generated image was 96432 bytes, with a four-byte-aligned
body instead of a 16-byte-aligned body. TelinkMiFlasher rejected it at file
selection with `Invalid size pointer in Telink OTA binary firmware!`, before
device write. R1 is intentionally not published as a firmware download.
