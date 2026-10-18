#!/usr/bin/env python3
"""Test production VDMA descriptors, overlap direction, bounds and failure paths."""
from pathlib import Path
import subprocess, tempfile
root=Path(__file__).resolve().parents[2]
source=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
static uint32_t regs[32];
static uint16_t memory[8192], expected[8192];
static unsigned locks, unlocks, starts, aborts;
static int fail;
static uint16_t me_dma_lock(void) { locks++; return 0x2300; }
static void me_dma_unlock(uint16_t sr) { assert(sr==0x2300); unlocks++; }
static void start(void) {
    uint32_t *d=&regs[16], row, x, w=d[1]&65535, h=d[1]>>16;
    int32_t sa=d[2]-0x800000, da=d[8]-0x800000;
    starts++;
    if(fail) { regs[1]=fail==1?1:0x14; return; }
    assert((d[0]&0x3ff)==0x1f0 && !(regs[0]&8));
    for(row=0;row<h;row++) {
        assert(da>=0 && da+2*w<=sizeof(memory));
        if(d[0]&0x800) {
            assert(sa>=0 && sa+2*w<=sizeof(memory));
            memmove((char*)memory+da,(char*)memory+sa,w*2);
        } else for(x=0;x<w;x++) memory[da/2+x]=(uint16_t)d[10];
        sa+=(int32_t)d[3]; da+=(int32_t)d[9];
    }
    regs[1]=2;
}
static void abort_job(void) { aborts++; regs[1]=0x74; }
#define ME_DMA_R(o) regs[(o)/4]
#define ME_DMA_START() start()
#define ME_DMA_ABORT() abort_job()
#include "dma.h"
int main(void) {
    struct me_dma_rect a={0x800000,256,80,24}, b={0x800200,256,80,24}, bad;
    unsigned i, previous;
    for(i=0;i<8192;i++) memory[i]=expected[i]=i;
    for(i=24;i;i--) memmove((char*)expected+512+(i-1)*256,
        (char*)expected+(i-1)*256,160);
    assert(me_dma_run(&a,&b,0)==1);
    assert(regs[16]&0x20000); assert((int32_t)regs[19]==-256);
    assert(!memcmp(memory,expected,sizeof memory));
    a=b; b.address=0x800000;
    for(i=0;i<24;i++) memmove((char*)expected+i*256,
        (char*)expected+512+i*256,160);
    assert(me_dma_run(&a,&b,0)==1 && !(regs[16]&0x20000));
    assert(!memcmp(memory,expected,sizeof memory));
    b.address=0x800002; b.width=31; b.height=4;
    assert(me_dma_run(0,&b,0x1234)==1);
    for(i=0;i<31;i++) assert(memory[i+1]==0x1234);
    assert(memory[0]==expected[0] && memory[32]==expected[32]);
    bad=b; bad.address=0x3ffffff0; assert(!me_dma_valid(&bad));
    bad=b; bad.address=0x7ffffe; assert(!me_dma_valid(&bad));
    bad=b; bad.address++; assert(!me_dma_valid(&bad));
    bad=b; bad.height=0; assert(!me_dma_valid(&bad));
    bad=b; bad.stride=0; assert(!me_dma_valid(&bad));
    bad=b; bad.stride=0xfffffffe; assert(!me_dma_valid(&bad));
    bad=b; bad.height=65536; assert(!me_dma_valid(&bad));
    previous=starts; assert(me_dma_run(0,&bad,0)==0 && starts==previous);
    regs[1]=1; assert(me_dma_run(0,&b,0)==0 && starts==previous);
    regs[1]=0; fail=1; assert(me_dma_run(0,&b,0)==-1 && aborts==1);
    fail=2; assert(me_dma_run(0,&b,0)==-1 && aborts==2);
    assert(locks==unlocks);
    puts("PASS: VDMA copy/fill, overlap directions, byte addresses, bounds, busy/error/timeout and cache-lock balance");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c=Path(tmp)/'dma.c'; exe=Path(tmp)/'dma'
    c.write_text(source)
    subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=undefined,address','-I'+str(root/'tools/fvdi/a2560me'),str(c),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
