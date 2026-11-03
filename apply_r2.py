"""Combine the published extension-only R2 bundle with a locally held OEM OTA."""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

ORIGINAL_SHA = 'd8ca0eb3d660a76d02e33fefa5d8b5186e1f2ccaa91ffb3584486822d18e4340'
R2_SHA = '8beab84985aba525b11101af9614f34c663e703bf2153416b53c981e3620e34b'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('original', type=Path)
    ap.add_argument('extension', type=Path)
    ap.add_argument('manifest', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    if a.output.exists():
        raise ValueError('Refusing to overwrite an existing output')
    original = a.original.read_bytes()
    if hashlib.sha256(original).hexdigest() != ORIGINAL_SHA:
        raise ValueError('Original SHA256 mismatch')
    ext = a.extension.read_bytes()
    if len(ext) != 3498:
        raise ValueError('Wrong R2 extension size')
    manifest = json.loads(a.manifest.read_text(encoding='utf8'))
    changes = manifest['changes']
    expected = {0x18:4,0xce2c:8,0xd0dc:8,0xd0fc:8,0xd154:8,0xd180:8}
    if len(changes) != len(expected) or {c['offset'] for c in changes} != set(expected):
        raise ValueError('Unexpected patch offsets')
    b = bytearray(original[:-4])
    b.extend(b'\xff' * (0x16b00-len(b)))
    b.extend(ext)
    b.extend(b'\xff' * (-len(b)%16))
    for c in changes:
        off = c['offset']
        new = bytes.fromhex(c['new'])
        if len(new) != expected[off] or original[off:off+len(new)].hex() != c['old']:
            raise ValueError('Patch preimage/size mismatch')
        b[off:off+len(new)] = new
    if struct.unpack_from('<I',b,0x18)[0] != len(b)+4:
        raise ValueError('Header length mismatch')
    b.extend(struct.pack('<I',zlib.crc32(b)^0xffffffff))
    if hashlib.sha256(b).hexdigest() != R2_SHA:
        raise ValueError('Final R2 SHA256 mismatch; no output written')
    a.output.write_bytes(b)
    if a.output.read_bytes() != b:
        raise IOError('Output read-back mismatch')
    print('R2 generated:', len(b), 'bytes;', R2_SHA)


if __name__ == '__main__':
    main()
