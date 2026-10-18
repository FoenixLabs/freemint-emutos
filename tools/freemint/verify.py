#!/usr/bin/env python3
"""Check board-critical instructions in the actual cross-built objects.

Usage: verify.py /path/to/freemint/sys
GPL-2.0-or-later; see doc/license.txt.
"""
from pathlib import Path
import re
import struct
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
kernel = Path(sys.argv[1])


def dump(path):
    return subprocess.check_output(
        ['m68k-atari-mint-objdump', '-dr', str(path)], text=True)


def block(text, name):
    return text.split('<' + name + '>:', 1)[1].split('\n\n', 1)[0]


# The hardware vector must dispatch through the replaceable _5MS cookie slot,
# preserving all registers and the exception frame for FreeMiNT's RTE chain.
trampoline = block(dump(root / 'obj/timer_.o'), '_a2560_int_5ms')
assert '_vector_5ms' in trampoline and '2f39' in trampoline
assert re.search(r'\b4e75\s+\trts', trampoline)
assert '_a2560_int_5ms' in block(dump(root / 'obj/timer.o'), '_init_system_timer')
keyboard = block(dump(root / 'obj/aciavecs.o'), '_call_kbdvec')
assert '_ikbdiorec' in keyboard and '_kbdvec' in keyboard
assert 'jsr %a1@' in keyboard and 'moveml %sp@+' in keyboard

# No compiler-generated FPU instructions in kernel C, and no STOP in the idle
# or halt paths. Handwritten guarded FPU context code is deliberately allowed.
objects = list((kernel / '.compile_060').glob('*.o'))
objects += [p for p in (kernel / 'arch/.compile_060').glob('*.o')
            if (kernel / 'arch' / (p.stem + '.c')).exists()]
assert objects
assert '_tos_filesys' in (kernel / '.compile_060/map.txt').read_text()
assert 'FS_NEWFATFS=D' in (root / 'drive_c/MINT/1-19-CUR/MINT.CNF').read_text()
for obj in objects:
    asm = dump(obj)
    assert not re.search(r'^\s*[0-9a-f]+:\t[^\t\n]+\t(?:f[a-z]+|stop|lpstop)\b', asm, re.M), str(obj)
detect = dump(kernel / 'arch/.compile_060/detect.o')
for name in ('_detect_fpu', '_detect_sfp'):
    code = block(detect, name)
    assert 'moveq #0,%d0' in code and 'rts' in code
    assert len(re.findall(r'^\s*[0-9a-f]+:', code, re.M)) == 2

prg = (root / 'drive_c/AUTO/MINT060.PRG').read_bytes()
magic, text, data, bss = struct.unpack('>HIII', prg[:14])
assert magic == 0x601a and text > 0 and bss > 0
assert len(prg) >= 28 + text + data
assert prg == (kernel / '.compile_060/mint060.prg').read_bytes()
rom = (root / 'emutos-a2560m.rom').read_bytes()
assert len(rom) == 512 * 1024
assert struct.unpack_from('>I', rom, 4)[0] == 0xffd00008
print('PASS: keyboard vector ABI, indirect _5MS timer, no C FPU/STOP, '
      'disabled FPU probes, staged kernel and 512 KiB flash ROM')
