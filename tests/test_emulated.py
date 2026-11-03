"""Execute compiled TC16 logic via instruction-by-instruction Thumb translation.
Not a TLSR8258 hardware/radio simulation. GPIO and sensors are explicit models.
"""
import re, struct, random, json
from pathlib import Path
from keystone import Ks, KS_ARCH_ARM, KS_MODE_THUMB
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn.arm_const import *
P=Path(__file__).resolve().parent.parent/'build'
BASE=0x16b00
ks=Ks(KS_ARCH_ARM,KS_MODE_THUMB)
data=bytearray((P/'extension.bin').read_bytes())
syms={m[2]:int(m[0],16) for line in (P/'extension.nm').read_text(encoding='utf-8-sig').splitlines() if len(m:=line.split())==3}
mapping={'tloadr':'ldr','tloadrb':'ldrb','tloadrh':'ldrh','tloadrsh':'ldrsh','tstorer':'str','tstorerb':'strb','tstorerh':'strh','tshftls':'lsls','tshftrs':'lsrs','tasrs':'asrs','tbclrs':'bics','tands':'ands','tors':'orrs','txors':'eors','tmuls':'muls','tnegs':'rsbs','tnand':'tst','taddcs':'adcs','tsubcs':'sbcs','tadd':'add','tsub':'sub','tadds':'adds','tsubs':'subs','tmov':'mov','tmovs':'movs','tcmp':'cmp','tpush':'push','tpop':'pop','tjex':'bx','tjl':'bl','tnop':'mov'}
count=0
for line in (P/'extension.dis').read_text(encoding='utf-8-sig').splitlines():
    m=re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{4}\s+)+)\s*(t\S+)\s*(.*)',line)
    if not m: continue
    addr=int(m[1],16); n=len(m[2].split())*2; op=m[3]; arg=m[4].split(';')[0].strip()
    arg=re.sub(r'\s*<[^>]*>','',arg)
    if op=='tnop': arg='r8, r8'
    if op=='tnegs': arg+=', #0'
    if op.startswith('tj') and op.endswith('.n'):
        op='b'+op[2:-2]; arg='0x'+arg
    else:
        if op=='tjl': arg='0x'+arg
        op=mapping[op]
    code=bytes(ks.asm(op+' '+arg,addr)[0])
    if len(code)!=n: raise ValueError((hex(addr),op,arg,n,code.hex()))
    data[addr-BASE:addr-BASE+n]=code;count+=1
(P/'emulation_thumb.bin').write_bytes(data)
regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
class VM:
    def __init__(self):
        self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB)
        self.u.mem_map(0,0x30000);self.u.mem_write(BASE,bytes(data))
        self.u.mem_map(0x800000,0x10000);self.u.mem_map(0x840000,0x10000)
        self.tick=10000;self.tx=[];self.scan=None;self.scan_status=0;self.mock=True
        self.addr=0x76;self.status=8;self.busy=False;self.badcrc=False;self.nack=False
        self.cal=struct.pack('<HhhHhhhhhhhh',27504,26435,-1000,36477,-10685,3024,2855,140,-7,15500,-14600,6000)
        self.raw=bytes.fromhex('655ac07eed00');self.rh=524288
        self.u.mem_write(0x800580,b'\x40');self.u.mem_write(0x800598,b'\x80')
        self.u.mem_write(0x800643,b'\x01')
        self.u.hook_add(UC_HOOK_CODE,self.hook)
        self.u.hook_add(UC_HOOK_MEM_READ,self.read)
        self.setscan(bytes([11,9])+b'LYWSD03MMC')
    def read(self,u,access,addr,size,value,user):
        if addr==0x800740:
            self.tick=(self.tick+160)&0xffffffff;u.mem_write(addr,struct.pack('<I',self.tick))
    def setscan(self,b):
        self.u.mem_write(0x845959,bytes([len(b)+6]));self.u.mem_write(0x845960,b)
    def ret(self,r):
        self.u.reg_write(UC_ARM_REG_R0,r);self.u.reg_write(UC_ARM_REG_PC,self.u.reg_read(UC_ARM_REG_LR))
    def hook(self,u,addr,size,user):
        if addr==0x20000:u.emu_stop();return
        if addr==0xf2fc:
            ptr,n=[u.reg_read(r) for r in regs[:2]]
            self.scan=bytes(u.mem_read(ptr,n))
            if not self.scan_status:self.setscan(self.scan)
            self.ret(self.scan_status);return
        if self.mock and addr==syms['bus_init']:self.ret(1);return
        if self.mock and addr==syms['bus_xfer']:
            a,tx,nt,rx=[u.reg_read(r) for r in regs]; nr=struct.unpack('<I',u.mem_read(u.reg_read(UC_ARM_REG_SP),4))[0]
            b=bytes(u.mem_read(tx,nt)) if nt else b'';self.tx.append((a,b.hex(),nr))
            result=b'';ok=not self.nack
            if a==0x38:
                if nr==1:result=bytes([self.status])
                if nr==7:
                    h=self.rh;t=400000
                    result=bytes([0x88 if self.busy else 8,h>>12,(h>>4)&255,((h&15)<<4)|(t>>16),(t>>8)&255,t&255])
                    c=crc(result);result+=bytes([c^int(self.badcrc)])
            elif a==self.addr:
                if b==b'\xd0':result=b'\x58'
                elif b==b'\xf3':result=b'\x00'
                elif b==b'\x88':result=self.cal
                elif b==b'\xf7':result=self.raw
            else:ok=False
            if ok and nr:
                assert len(result)==nr,(a,b,nr,result)
                u.mem_write(rx,result)
            self.ret(int(ok))
    def call(self,name,*args):
        u=self.u;u.reg_write(UC_ARM_REG_SP,0x847f00);u.reg_write(UC_ARM_REG_LR,0x20001)
        for r,a in zip(regs,args):u.reg_write(r,a&0xffffffff)
        for i,a in enumerate(args[4:]):u.mem_write(0x847f00+4*i,struct.pack('<I',a))
        for r in [UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]:u.reg_write(r,0x12345678)
        u.emu_start(syms[name]|1,0x20000,count=1000000)
        assert u.reg_read(UC_ARM_REG_PC)==0x20000,(name,hex(u.reg_read(UC_ARM_REG_PC)))
        assert u.reg_read(UC_ARM_REG_SP)==0x847f00
        for r in [UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]:assert u.reg_read(r)==0x12345678,(name,r)
        return u.reg_read(UC_ARM_REG_R0)
    def sample(self):return struct.unpack('<iHH',self.u.mem_read(0x847294,8))
def crc(b):
    c=255
    for x in b:
        c^=x
        for _ in range(8):c=((c<<1)^(0x31 if c&128 else 0))&255
    return c
results=[]
def check(name,fn):fn();results.append(name)
def normal(addr=0x76,rh=524288):
    v=VM();v.addr=addr;v.rh=rh
    assert v.call('mod_detect')==1 and v.u.mem_read(0x847253,1)==b'\x02'
    v.call('mod_init');v.call('mod_start')
    assert v.call('mod_poll')==2
    v.tick=(v.tick+1600000)&0xffffffff
    assert v.call('mod_poll')==1
    assert v.sample()==(2508,(rh*10000+524288)>>20,1),v.sample()
    assert v.scan[-4:]==bytes.fromhex('042d8901'),v.scan.hex() # 100653Pa
    assert v.scan[:12]==bytes([11,9])+b'LYWSD03MMC'
    return v
check('BMP Bosch reference / AHT 50% / no U1',normal)
check('BMP alternate address 0x77',lambda:normal(0x77))
check('AHT 0%',lambda:normal(rh=0))
check('AHT maximum',lambda:normal(rh=1048575))
def faults():
    for fault in ['badcrc','nack','zero_cal','invalid_raw','busy']:
        v=VM();v.call('mod_init');v.call('mod_start');v.tick+=1600000
        if fault=='zero_cal':v.cal=bytes(24)
        elif fault=='invalid_raw':v.raw=b'\x80\x00\x00'*2
        else:setattr(v,fault,True)
        r=v.call('mod_poll')
        assert r==(2 if fault=='busy' else 0),(fault,r)
        assert v.sample()[2]==0
        v.tick+=8000001;assert v.call('mod_poll')==0
check('CRC/NACK/calibration/raw/busy/timeout rejection',faults)
def cal_wrap():
    v=VM();v.status=0;v.tick=0xffff0000;v.call('mod_init');v.call('mod_start')
    assert v.u.mem_read(0x847291,1)==b'\x02'
    assert v.call('mod_poll')==2
    v.status=8;v.tick=(v.tick+400000)&0xffffffff;assert v.call('mod_poll')==2
    v.tick=(v.tick+1600000)&0xffffffff;assert v.call('mod_poll')==1
check('asynchronous AHT initialization and timer wrap',cal_wrap)
def scan():
    v=normal();assert v.call('pressure_scan',-1234,7000,99999,9)==1
    assert len(v.scan)==29 and v.scan[19:22]==b'\x02.\xfb'
    for b in [bytes([30,255])+bytes(29),bytes([15,9])+b'bad',bytes([0])]:
        v.setscan(b);v.scan=None;assert v.call('pressure_scan',1,2,3,4)==0;assert v.scan is None
    v.setscan(bytes([11,9])+b'LYWSD03MMC');v.scan_status=12
    before=bytes(v.u.mem_read(0x845960,12));assert v.call('pressure_scan',1,2,3,4)==0
    assert bytes(v.u.mem_read(0x845960,12))==before
check('scan response idempotence / no room / malformed / API busy',scan)
def runtime():
    rng=random.Random(130)
    for _ in range(100):
        a=rng.getrandbits(64);b=rng.getrandbits(64);v=VM()
        v.call('__muldi3',a&0xffffffff,a>>32,b&0xffffffff,b>>32)
        r=v.u.reg_read(UC_ARM_REG_R0)|(v.u.reg_read(UC_ARM_REG_R1)<<32)
        assert r==a*b&((1<<64)-1)
        a=rng.randrange(-(1<<62),1<<62);b=rng.randrange(1,1<<35)
        v.call('__divdi3',a&0xffffffff,(a>>32)&0xffffffff,b&0xffffffff,b>>32)
        r=v.u.reg_read(UC_ARM_REG_R0)|(v.u.reg_read(UC_ARM_REG_R1)<<32)
        expect=(abs(a)//b)*(-1 if a<0 else 1)
        assert r==expect&((1<<64)-1)
check('compiled 64-bit runtime: 100 randomized multiply/divide pairs',runtime)
def gpio_faults():
    for scl in [0,128]:
        v=VM();v.mock=False;v.u.mem_write(0x800598,bytes([scl]));v.u.mem_write(0x846000,b'\xac3\x00')
        assert v.call('bus_init')==1
        assert v.call('bus_xfer',0x38,0x846000,3,0,0)==0
        assert v.u.mem_read(0x800582,1)[0]&64 and v.u.mem_read(0x80059a,1)[0]&128
        assert not(v.u.mem_read(0x800583,1)[0]&64 or v.u.mem_read(0x80059b,1)[0]&128)
check('compiled GPIO: SCL held low / absent sensor NACK / released outputs',gpio_faults)
report={'translated_instructions':count,'passed':results,'limits':'Instruction-equivalence simulation, not TC32 silicon or MiHome radio validation.'}
(P/'test_results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
