"""Create an extension-only release; never include an OEM-derived full image."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT/'build'
manifest = json.loads((BUILD/'patch_manifest.json').read_text(encoding='utf8'))
if manifest['patched_sha256'] != '8beab84985aba525b11101af9614f34c663e703bf2153416b53c981e3620e34b':
    raise ValueError('Not the reference R2 build')
if hashlib.sha256((BUILD/'extension.bin').read_bytes()).hexdigest() != 'a43d3925e61919007fb7e38e3903899d02cce4f0ecca9a59cca5b40326cc8eec':
    raise ValueError('Wrong extension bytes')
entries = {n:(ROOT/n).read_bytes() for n in ['apply_r2.py','restore_ota.py','fetch_inputs.py','LICENSE']}
entries['README.md'] = (ROOT/'docs/extension-bundle.md').read_bytes()
entries['extension.bin'] = (BUILD/'extension.bin').read_bytes()
entries['patch_manifest.json'] = (BUILD/'patch_manifest.json').read_bytes()
entries['SHA256SUMS'] = ''.join(hashlib.sha256(b).hexdigest()+'  '+n+'\n' for n,b in sorted(entries.items())).encode()
out = BUILD/'lywsd03mmc-0130-b2-r2-extension-only.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for n,b in sorted(entries.items()):
        info = zipfile.ZipInfo(n,(2026,11,3,0,0,0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info,b)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    assert set(z.namelist()) == set(entries)
    assert all(z.read(n) == b for n,b in entries.items())
print(out.name, out.stat().st_size, hashlib.sha256(out.read_bytes()).hexdigest())
