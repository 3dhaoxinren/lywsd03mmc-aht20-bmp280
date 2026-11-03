"""Fetch public reference inputs, verify hashes, keep them OUTSIDE Git."""
import argparse
import hashlib
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM = 'https://raw.githubusercontent.com/pvvx/ATC_MiThermometer/b02b5137c14461daa7db1615e4fd9739b7a20ddd'
ORIGINAL_URL = UPSTREAM + '/bin/Original/Original_OTA_Xiaomi_LYWSD03MMC_v1.0.0_0130.bin'
ORIGINAL_SHA = 'd8ca0eb3d660a76d02e33fefa5d8b5186e1f2ccaa91ffb3584486822d18e4340'
TC_URL = 'https://doc.telink-semi.cn/tools/vsc/windows/toolchains/tc32_130_Windows.tar.xz'
TC_SHA = 'f1763ed4a212000dd0b585fc718a7a602bbe059638b13cc7bb0c8b4e189ee620'


def fetch(url, dest, expected):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        tmp = dest.with_suffix(dest.suffix + '.download')
        subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--connect-timeout', '20',
                        '--max-time', '600', url, '--output', str(tmp)], check=True)
        if hashlib.sha256(tmp.read_bytes()).hexdigest() != expected:
            raise ValueError('Downloaded SHA256 mismatch: ' + dest.name)
        tmp.replace(dest)
    if hashlib.sha256(dest.read_bytes()).hexdigest() != expected:
        raise ValueError('Existing SHA256 mismatch: ' + dest.name)
    print('Verified:', dest.name, expected)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--toolchain', action='store_true', help='Also fetch/extract Windows TC32 tools')
    args = ap.parse_args()
    fetch(ORIGINAL_URL, ROOT / 'inputs/original_0130.bin', ORIGINAL_SHA)
    if args.toolchain:
        archive = ROOT / '.cache/tc32_130_Windows.tar.xz'
        fetch(TC_URL, archive, TC_SHA)
        with tarfile.open(archive, 'r:xz') as tar:
            tar.extractall(ROOT / '.cache/toolchain', filter='data')
        print('Toolchain root:', ROOT / '.cache/toolchain/tc32')
