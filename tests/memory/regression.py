#!/usr/bin/env python3
"""Exercise production BIOS allocation and A2560Me memory reservations.

Distributed under GPL version 2 or later; see doc/license.txt.
"""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]


def function(path, signature):
    source = (root / path).read_text()
    start = source.index(signature + '\n{')
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


binding = re.search(r'^#define Balloc\(.*$',
                    (root / 'include/biosbind.h').read_text(), re.M)[0]
prefix = r'''
#include <stdint.h>
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
typedef unsigned char UBYTE;
typedef uintptr_t ULONG;
typedef intptr_t LONG;
typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define MACHINE_A2560M 1
#define KDEBUG(x) ((void)0)
#define MAYBE_UNUSED(x) ((void)(x))
#define panic(...) abort()
static UBYTE ram[0x800000];
static UBYTE *_text, *_edata, *_end_os_stram;
static UBYTE *membot, *memtop, *end_os, *phystop;
static UBYTE *video_ram_addr, *v_bas_ad;
static LONG video_ram_size;
#define VSRAM_BANK0 (ram + 0x700000)
static LONG calc_vram_size(void) { return 1280L/8*960+256; }
'''
dispatch = r'''
static UBYTE *bios_l_lw(int op, ULONG size, BOOL top)
{
    assert(op == 13);
    return balloc_stram(size, top);
}
'''
test = r'''
int main(void)
{
    UBYTE *buffers;
    ULONG n = 4UL * (20 + 16384);
    _end_os_stram = ram + 0x12224;
    _text = ram + 0x100000;
    _edata = ram + 0x140004;
    phystop = ram + sizeof(ram);
    bmem_init();
    assert(membot == _edata && end_os == membot);
    setup_video_ram();
    assert(memtop == ram + 0x700000);
    assert(v_bas_ad == memtop);
    buffers = Balloc(FALSE, n);
    assert(buffers == _edata);
    assert(membot == buffers + n);
    assert(buffers + n <= memtop);
    assert(Balloc(TRUE, 1024UL) == ram + 0x700000 - 1024);
    assert(memtop == ram + 0x700000 - 1024);
    /* A flash image must not move the allocator into flash. */
    _text = (UBYTE *)(uintptr_t)0xffc00000;
    _edata = (UBYTE *)(uintptr_t)0xffc40004;
    bmem_init();
    assert(membot == _end_os_stram);
    puts("PASS: Balloc argument order/width, RAM image reservation, framebuffer exclusion, flash layout");
}
'''
source = prefix
source += function('bios/biosmem.c', 'void bmem_init(void)')
source += function('bios/biosmem.c', 'UBYTE *balloc_stram(ULONG size, BOOL top)')
source += function('bios/screen.c', 'static void setup_video_ram(void)')
source += dispatch + '\n' + binding + '\n' + test
with tempfile.TemporaryDirectory(prefix='memory-regression-') as directory:
    c = Path(directory) / 'test.c'
    exe = Path(directory) / 'test'
    c.write_text(source)
    subprocess.run(['cc', '-std=c99', '-fsanitize=address,undefined',
                    str(c), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
