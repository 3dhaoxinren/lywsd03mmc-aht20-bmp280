# Third-party notices

## PVVX / ATC_MiThermometer

Upstream: https://github.com/pvvx/ATC_MiThermometer

Pinned reference commit: `b02b5137c14461daa7db1615e4fd9739b7a20ddd`.

The GPIO mapping and archived original OTA reference were researched there.
`third_party/telink_flasher_validation.js` contains the CRC32 and
`testOTAFirmware` routines extracted from the public
https://pvvx.github.io/ATC_MiThermometer/TelinkMiFlasher.html page to test the
same file-format rejection observed on the first build. This is an offline
snapshot, not a promise of compatibility with future flasher revisions.

The upstream permission/warranty notice is retained verbatim in
`third_party/PVVX-LICENSE.txt`. Attribution: pvvx and ATC_MiThermometer contributors;
the project is forked from atc1441/ATC_MiThermometer.

## Xiaomi / Mijia OEM image and Telink tools

The original Xiaomi LYWSD03MMC 0130 OTA and Telink toolchain are external
inputs. They are not distributed in this repository and are not relicensed
under this project's MIT license. Their respective owners retain their rights.
The patcher verifies exact SHA256 values before local use. Generated full
images are ignored by Git; possession of source code here does not grant
redistribution rights to the OEM image or its modified derivative.

## Sensor documentation and protocols

- Bosch BMP280 DS001 rev1.26 compensation specification:
  https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf
- Aosong AHT20 product manual:
  https://www.aosong.com/userfiles/files/media/AHT20%20%E8%8B%B1%E6%96%87%E7%89%88%E8%AF%B4%E6%98%8E%E4%B9%A6%20A0%2020201222.pdf
- BTHome v2 format: https://bthome.io/format/

Documentation and protocol references are not claims of affiliation or
endorsement. Unicorn and Keystone are test dependencies installed separately,
not vendored into this repository.
