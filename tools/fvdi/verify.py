#!/usr/bin/env python3
"""Check actual fVDI/diagnostic objects and matching DDR reservations.
GPL-2.0-or-later; see doc/license.txt.
"""
from pathlib import Path
import re
import struct
import subprocess

root=Path(__file__).resolve().parents[2]
repo=root.parent/'fvdi/fvdi'
driver=repo/'drivers/a2560me'
assert (root/'foenix/a2560me_memory.h').read_bytes()==(driver/'a2560me_memory.h').read_bytes()
for name,built in [('FVDI.PRG',repo/'engine/fvdi_gnu.prg'),('A2560ME.SYS',driver/'a2560me.sys')]:
    data=(root/'drive_d/MINT/FVDI'/name).read_bytes()
    assert data==built.read_bytes() and data[:2]==b'\x60\x1a'
objects=list((repo/'engine').glob('*.o'))+list(driver.glob('*.o'))
objects+=list((root/'logs/fvdi/probe-build').glob('*.o'))
assert len(objects)>25
for obj in objects:
    asm=subprocess.check_output(['m68k-atari-mint-objdump','-d',str(obj)],text=True)
    assert not re.search(r'^\s*[0-9a-f]+:\t[^\t\n]+\t(?:f[a-z]+|stop|lpstop)\b',asm,re.M), obj
for name in ('RAMTEST.TOS','GUIPAT.TOS','DMATEST.TOS'):
    data=(root/'drive_d/MINT/FVDI'/name).read_bytes()
    assert data[:2]==b'\x60\x1a'
    text,init,bss=struct.unpack_from('>III',data,2)
    assert len(data)>=28+text+init and bss>=16384
# fVDI is active in the copy-ready package; monochrome recovery remains separate.
normal=(root/'drive_d/MINT/MINT.CNF').read_text().lower()
optional=(root/'drive_d/MINT/FVDI.CNF').read_text().lower()
assert normal == optional
assert optional.index('cd u:/d/mint/fvdi') < optional.index('exec u:/d/mint/fvdi/fvdi.prg') < optional.index('gem=')
assert 'exec u:/d/mint/fvdi/fvdi.prg' not in (root/'drive_d/MINT/MONO.CNF').read_text().lower()
rom=(root/'emutos-a2560m.rom').read_bytes()
assert len(rom)==512*1024 and struct.unpack_from('>I',rom,4)[0]==0xffd00008
print('PASS: fVDI/driver/probe headers and build identity, no FPU/STOP, shared DDR map and active colour startup and separate monochrome recovery')
