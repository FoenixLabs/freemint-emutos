#!/usr/bin/env python3
"""Exercise the production DDR registration on two mapped boundary pages.
GPL-2.0-or-later; see doc/license.txt.
"""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
source=(root/'bios/memory2.c').read_text()
start=source.index('static void a2560me_add_ddr(void)\n{')
end=source.index('\n#endif',source.index('    else\n        KDEBUG(("DDR3 boundary test',start))
function=source[start:end]
prefix=r'''
#define _GNU_SOURCE
#include <stdint.h>
#include <assert.h>
#include <sys/mman.h>
#include <stdio.h>
#include "a2560me_memory.h"
typedef uint32_t ULONG;
typedef intptr_t LONG;
typedef unsigned char UBYTE;
typedef int BOOL;
#define CONF_WITH_BUS_ERROR 1
#define KDEBUG(x) ((void)0)
static ULONG control;
#define R32(a) control
static int readable=1, corrupt, reject_alloc;
static unsigned added, cookies;
static long check_read_byte(LONG address) {
    assert(address==A2560ME_DDR_BASE || address==A2560ME_VIDEO_BASE-4);
    return readable;
}
static void flush_data_cache(void *p,long n) { (void)p; assert(n==4); }
static void invalidate_data_cache(void *p,long n) {
    assert(n==4);
    if (corrupt && (uintptr_t)p==A2560ME_VIDEO_BASE-4 && *(ULONG *)p==0xaa55fedc)
        *(ULONG *)p ^= 1;
}
static long xmaddalt(UBYTE *p, ULONG n) {
    assert((uintptr_t)p==A2560ME_DDR_BASE);
    assert(n==1008UL*1024*1024 && (uintptr_t)p+n==A2560ME_VIDEO_BASE);
    added++; return reject_alloc ? -1:0;
}
static void cookie_add(ULONG tag,ULONG value) {
    assert(tag==0x4656524d && value==A2560ME_VIDEO_BASE); cookies++;
}
'''
test=r'''
int main(void) {
    volatile ULONG *first=(volatile ULONG *)A2560ME_DDR_BASE;
    volatile ULONG *last=(volatile ULONG *)(A2560ME_VIDEO_BASE-4);
    assert(mmap((void *)A2560ME_DDR_BASE,4096,PROT_READ|PROT_WRITE,
        MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0)!=(void *)-1);
    assert(mmap((void *)(A2560ME_VIDEO_BASE-4096),4096,PROT_READ|PROT_WRITE,
        MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0)!=(void *)-1);
    *first=0x1234abcd; *last=0xfedc9876;
    a2560me_add_ddr();
    assert(added==1 && cookies==1);
    assert(*first==0x1234abcd && *last==0xfedc9876);
    control=0x40; a2560me_add_ddr(); assert(added==1);
    control=0; readable=0; a2560me_add_ddr(); assert(added==1);
    readable=1; corrupt=1; a2560me_add_ddr(); assert(added==1 && cookies==1);
    assert(*first==0x1234abcd && *last==0xfedc9876);
    corrupt=0; reject_alloc=1; a2560me_add_ddr(); assert(added==2 && cookies==1);
    puts("PASS: DDR registration bounds, endian/unmapped/corrupt guards, preserved contents and reservation cookie");
    return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c=Path(tmp)/'ddr.c'; exe=Path(tmp)/'ddr'
    c.write_text(prefix+function+test)
    subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',
        '-I'+str(root/'foenix'),str(c),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
