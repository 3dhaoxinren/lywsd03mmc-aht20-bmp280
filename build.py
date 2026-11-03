"""Build the experimental R2 extension, guard-patch exact stock 0130, run tests."""
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from fetch_inputs import ORIGINAL_SHA
from restore_ota import restore

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / 'build'
NAME = 'LYWSD03MMC_0130_B2_P8SDA_P7SCL_BMPtemp_AHThum_EXPERIMENTAL_R2.bin'
REFERENCE_SHA = '8beab84985aba525b11101af9614f34c663e703bf2153416b53c981e3620e34b'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--toolchain', type=Path, default=Path(os.environ.get('TC32_HOME', ROOT / '.cache/toolchain/tc32')))
    ap.add_argument('--verify-reference', action='store_true')
    a = ap.parse_args()
    tc = a.toolchain.resolve() / 'bin'
    gcc = tc / 'tc32-elf-gcc.exe'
    if not gcc.exists():
        raise SystemExit('Windows TC32 compiler missing. Run python fetch_inputs.py --toolchain or set TC32_HOME.')
    original = (ROOT / 'inputs/original_0130.bin').read_bytes()
    if sha(original) != ORIGINAL_SHA:
        raise ValueError('Wrong original firmware. No files patched.')
    assert struct.unpack_from('<I', original, len(original)-4)[0] == zlib.crc32(original[:-4]) ^ 0xffffffff
    BUILD.mkdir(exist_ok=True)
    env = dict(os.environ)
    env['PATH'] = str(tc) + os.pathsep + env['PATH']
    env['PYTHONUTF8'] = '1'
    commands = []

    def run(args, output=None):
        r = subprocess.run([str(x) for x in args], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        s = r.stdout.decode('utf8', errors='replace')
        commands.append({'command': [str(x) for x in args], 'exit': r.returncode, 'output': s})
        (BUILD / 'commands.json').write_text(json.dumps(commands, indent=2), encoding='utf8')
        if r.returncode:
            raise RuntimeError(s)
        if output:
            output.write_text(s, encoding='utf8')
        return s

    run([gcc, '-Os', '-std=c99', '-ffreestanding', '-fno-builtin', '-fno-strict-aliasing',
         '-ffunction-sections', '-fdata-sections', '-Wall', '-Wextra', '-Werror', '-nostdlib',
         '-Wl,-T,patch.ld,-Map,build/extension.map', '-o', 'build/extension.elf', 'sensor_mod.c', 'runtime64.c'])
    run([tc/'tc32-elf-objcopy.exe', '-O', 'binary', 'build/extension.elf', 'build/extension.bin'])
    run([tc/'tc32-elf-objdump.exe', '-d', 'build/extension.elf'], BUILD/'extension.dis')
    run([tc/'tc32-elf-nm.exe', '-n', 'build/extension.elf'], BUILD/'extension.nm')
    run([tc/'tc32-elf-size.exe', 'build/extension.elf'], BUILD/'size.txt')
    syms = {s[2]:int(s[0],16) for line in (BUILD/'extension.nm').read_text().splitlines() if len(s:=line.split())==3}
    extension = (BUILD/'extension.bin').read_bytes()
    b = bytearray(original[:-4])
    b.extend(b'\xff' * (0x16b00-len(b)))
    b.extend(extension)
    b.extend(b'\xff' * (-len(b) % 16))
    changes = []

    def replace(off, new, why):
        old = bytes(b[off:off+len(new)])
        b[off:off+len(new)] = new
        changes.append({'offset':off, 'offset_hex':hex(off), 'old':old.hex(), 'new':new.hex(), 'reason':why})

    hooks = {0xce2c:'mod_detect',0xd0dc:'mod_init',0xd0fc:'mod_init',0xd154:'mod_start',0xd180:'mod_poll'}
    for off, name in hooks.items():
        assert off % 4 == 0
        replace(off, struct.pack('<HHI', 0x0b00, 0x0718, syms[name] | 1), name)
    replace(0x18, struct.pack('<I',len(b)+4), 'image length')
    b.extend(struct.pack('<I',zlib.crc32(b)^0xffffffff))
    assert len(b) < 0x20000 and len(b)%16 == 4
    assert struct.unpack_from('<I', b, 0x18)[0] == len(b)
    allowed = set(range(0x18,0x1c))
    for off in hooks:
        allowed.update(range(off,off+8))
    assert all(original[i] == b[i] for i in range(len(original)-4) if i not in allowed)
    if a.verify_reference and sha(b) != REFERENCE_SHA:
        raise ValueError('Rebuilt image differs from R2 reference')
    out = BUILD / NAME
    out.write_bytes(b)
    manifest = {'original_sha256':ORIGINAL_SHA,'original_size':len(original),'patched_sha256':sha(b),
                'patched_size':len(b),'changes':changes,'extension_address':'0x16b00',
                'extension_size':len(extension),'original_crc_trailer':original[-4:].hex(),
                'scope':'0130 B2.0 only; experimental; see docs/validation.md'}
    mp = BUILD / 'patch_manifest.json'
    mp.write_text(json.dumps(manifest,indent=2),encoding='utf8')
    run([sys.executable, 'tests/test_emulated.py'])
    run(['node', 'tests/test_flasher.cjs', out])
    run([sys.executable, 'tests/test_hooks.py'])
    with tempfile.TemporaryDirectory(dir=BUILD) as td:
        extra = Path(td)/'patched-copy.bin'
        extra.write_bytes(b)
        restored = Path(td)/'restored.bin'
        restore(extra,restored,mp)
        assert restored.read_bytes() == original
        invalid = bytearray(b)
        invalid[0x16b00] ^= 1
        extra.write_bytes(invalid)
        try:
            restore(extra,Path(td)/'must-not-exist.bin',mp)
        except ValueError:
            pass
        else:
            raise AssertionError('Corrupt restore input accepted')
        assert not (Path(td)/'must-not-exist.bin').exists()
    assert out.read_bytes() == b
    summary = {'image_size':len(b),'sha256':sha(b),'reference_matches':sha(b)==REFERENCE_SHA,
               'restore_exact':True,'corrupt_restore_rejected':True,
               'source_sha256':{n:sha((ROOT/n).read_bytes()) for n in ['sensor_mod.c','runtime64.c','patch.ld']}}
    (BUILD/'verification.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
