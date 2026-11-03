"""Check actual image hooks and execute equivalent tail jumps in the model."""
import json
import runpy
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ns = runpy.run_path(str(ROOT/'tests/test_emulated.py'))
manifest = json.loads((ROOT/'build/patch_manifest.json').read_text(encoding='utf8'))
image = (ROOT/'build/LYWSD03MMC_0130_B2_P8SDA_P7SCL_BMPtemp_AHThum_EXPERIMENTAL_R2.bin').read_bytes()
v = ns['VM']()
for c in manifest['changes']:
    if c['reason'] == 'image length':
        continue
    off = c['offset']
    load, jump, dest = struct.unpack_from('<HHI',image,off)
    assert (load,jump) == (0x0b00,0x0718)
    assert dest & 1 and 0x16b00 <= dest & ~1 < len(image)-4
    v.u.mem_write(off,struct.pack('<HHI',0x4b00,0x4718,dest))
    ns['syms']['hook_'+c['reason']] = off
assert v.call('hook_mod_detect') == 1
v.call('hook_mod_init')
v.call('hook_mod_start')
v.tick += 1600000
assert v.call('hook_mod_poll') == 1
assert v.sample() == (2508,5000,1)
report = {'all_five_hooks_valid':True,'tail_jump_execution':'passed',
          'limit':'Instruction-equivalence model, not hardware execution'}
(ROOT/'build/hook_validation.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
