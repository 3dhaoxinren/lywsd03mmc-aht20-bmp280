"""Restore a matching patched OTA FILE, not device flash or binding keys."""
import argparse
import hashlib
import json
from pathlib import Path


def restore(src, dst, manifest):
    if src.resolve() == dst.resolve():
        raise ValueError('Input and output paths must differ')
    if dst.exists():
        raise ValueError('Refusing to overwrite an existing output file')
    m = json.loads(manifest.read_text(encoding='utf8'))
    b = bytearray(src.read_bytes())
    if hashlib.sha256(b).hexdigest() != m['patched_sha256']:
        raise ValueError('Input SHA256 mismatch')
    for c in m['changes']:
        old = bytes.fromhex(c['old'])
        b[c['offset']:c['offset'] + len(old)] = old
    b = b[:m['original_size'] - 4] + bytes.fromhex(m['original_crc_trailer'])
    if hashlib.sha256(b).hexdigest() != m['original_sha256']:
        raise ValueError('Restored SHA256 mismatch')
    dst.write_bytes(b)
    if dst.read_bytes() != b:
        raise IOError('Output read-back mismatch')
    print('Restored exact original OTA:', m['original_sha256'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--manifest', type=Path)
    a = ap.parse_args()
    restore(a.input, a.output, a.manifest or a.input.parent / 'patch_manifest.json')
