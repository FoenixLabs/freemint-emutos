#!/usr/bin/env python3
"""Check staged GUI files against build objects and boot configuration.

GPL-2.0-or-later; see doc/license.txt.
"""
from pathlib import Path
import re
import struct
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
work = Path(sys.argv[1])
xa = work / 'freemint/xaaes/src.km'
pairs = [(xa / '.compile_02060/xaaes020.km', 'MINT/XAAES/XAAES020.KM'),
         (xa / 'xaloader/.compile_02060/xaloader.prg', 'MINT/XAAES/XALOADER.PRG'),
         (xa / 'adi/whlmoose/.compile_02060/moose.adi', 'MINT/XAAES/MOOSE.ADI')]
for source, target in pairs:
    data = (root / 'drive_d' / target).read_bytes()
    assert data == source.read_bytes(), target
    assert struct.unpack_from('>H', data)[0] == 0x601a, target
    text, initialized, bss = struct.unpack_from('>III', data, 2)
    assert text and len(data) >= 28 + text + initialized, target

# Check every compiled C object, including VDI bindings. Assembly trampolines
# are reviewed separately; they contain no FPU or board idle instructions.
objects = []
for folder in [xa, xa / 'xaloader', xa / 'adi/whlmoose']:
    objects += [p for p in (folder / '.compile_02060').glob('*.o')
                if (folder / (p.stem + '.c')).exists()]
objects += list((work / 'gemlib/.lib68020-60.short').glob('*.o'))
assert len(objects) > 100
for obj in objects:
    asm = subprocess.check_output(['m68k-atari-mint-objdump', '-d', str(obj)], text=True)
    assert not re.search(r'^\s*[0-9a-f]+:\t[^\t\n]+\t(?:f[a-z]+|stop|lpstop)\b', asm, re.M), obj

for name in ('XAAES.RSC', 'XAAESWDG.RSC', 'XA_XTOBJ.RSC'):
    data = (root / 'drive_d/MINT/XAAES' / name).read_bytes()
    assert len(data) >= 36 and struct.unpack_from('>H', data, 34)[0] <= len(data)
assert len((root / 'drive_d/DESKTOP/DESKTOP.PRG').read_bytes()) > 100000
assert struct.unpack_from('>H', (root / 'drive_d/DESKTOP/DESKTOP.PRG').read_bytes())[0] == 0x601a
cnf = (root / 'drive_d/MINT/MINT.CNF').read_text()
assert 'GEM=u:/d/mint/xaaes/xaloader.prg u:/d/mint/xaaes/xaaes020.km' in cnf
recovery = (root / 'drive_d/MINT/SHELL.CNF').read_text()
assert not re.search(r'^\s*(?:GEM|INIT)\s*=', recovery, re.M)
xa_cnf = (root / 'drive_d/MINT/XAAES/XAAES.CNF').read_text()
assert 'screendev = 1' in xa_cnf and 'shell = u:/d/desktop/desktop.prg' in xa_cnf
assert not (root / 'drive_c/MINT/1-19-CUR/MOOSE.ADI').exists()
print('PASS: GUI module headers, staged build identity, no C FPU/STOP, '
      'resource files, explicit D: loader paths and shell recovery')
