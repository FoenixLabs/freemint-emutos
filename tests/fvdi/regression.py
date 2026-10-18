#!/usr/bin/env python3
"""Exercise production register transitions against a guarded mock framebuffer.
GPL-2.0-or-later; see doc/license.txt.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
prefix = r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
static uint32_t regs[16], mock_pixels[8*1024*1024/4];
static uint16_t mouse;
static uint32_t cache = 0x80c08000;
static unsigned cache_calls;
static uint32_t *reg32(unsigned long a) {
    if (a == 0xfec80000UL) return &regs[0];
    if (a == 0xfec80004UL) return &regs[1];
    if (a == 0xfec00000UL) return &regs[2];
    if (a == 0xfd000000UL) return &regs[3];
    assert(a >= 0xfc000000UL && a <= 0xfc000010UL && !(a&3));
    return &regs[4+(a-0xfc000000UL)/4];
}
static uint16_t *reg16(unsigned long a) { assert(a==0xfec80c00UL); return &mouse; }
#define ME_R32(a) (*reg32(a))
#define ME_R16(a) (*reg16(a))
#define ME_PIXELS mock_pixels
#include "video.h"
static uint32_t me_disable_dcache(void) {
    uint32_t old=cache; cache &= 0x7fffffff; cache_calls++; return old;
}
static void me_restore_dcache(uint32_t saved) {
    cache = (cache & 0x7fffffff) | (saved & 0x80000000); cache_calls++;
}
int main(void) {
    struct me_video_state state = {0};
    uint32_t saved[16];
    unsigned i, n;
    assert(A2560ME_DDR_BASE + A2560ME_ALT_SIZE == A2560ME_VIDEO_BASE);
    assert(A2560ME_VIDEO_BASE + A2560ME_VIDEO_SIZE == A2560ME_DDR_TOP);
    assert(A2560ME_ALT_SIZE == 1008UL*1024*1024);
    assert(!(A2560ME_VIDEO_BASE&31));
    regs[0] = 0x80124003; regs[1] = 0x08080801; mouse=0x81;
    for(i=4;i<=8;i++) regs[i] = i*0x12345;
    memcpy(saved,regs,sizeof regs);
    regs[2]=0x40; assert(!me_video_enter(&state,0)); assert(cache_calls==0);
    regs[2]=0; regs[3]=1; assert(!me_video_enter(&state,0)); assert(cache_calls==0);
    regs[3]=0;
    for(i=0;i<sizeof mock_pixels/sizeof mock_pixels[0];i++) mock_pixels[i]=0xdeadbeef;
    assert(me_video_enter(&state,0));
    assert(state.active && cache==0x00c08000);
    assert(ME_R32(ME_GUI)==13 && ME_R32(ME_GUI+4)==A2560ME_VIDEO_BASE);
    assert(ME_R32(ME_GUI+12)==2560 && !(mouse&1));
    assert((ME_R32(ME_MASTER)&(ME_TOSGRAPH|ME_MEMTEXT|0x1403))==0);
    assert(ME_R32(ME_MASTER)&ME_GRAPHICS);
    n=1280*960/2;
    for(i=0;i<n;i++) assert(mock_pixels[i]==0);
    assert(mock_pixels[n]==0xdeadbeef);
    mock_pixels[0]=0x12345678;
    assert(me_video_enter(&state,0) && mock_pixels[0]==0x12345678 && cache_calls==1);
    me_video_leave(&state);
    assert(memcmp(saved,regs,sizeof regs)==0 && mouse==0x81 && cache==0x80c08000);
    assert(!state.active);
    me_video_leave(&state); assert(cache_calls==2);
    regs[0] |= ME_VIDEO1024;
    assert(me_height(0)==1024 && me_height(1)==512);
    assert(me_video_enter(&state,1));
    assert(ME_R32(ME_GUI)==5 && ME_R32(ME_GUI+12)==1280);
    me_video_leave(&state);
    puts("PASS: DDR reservation, endian/GGE guards, RGB565 mode/byte address/stride, clear bounds, cache and monochrome restoration");
    return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp)/'test.c'; exe=Path(tmp)/'test'
    c.write_text(prefix)
    subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined','-I'+str(root/'tools/fvdi/a2560me'),
                    str(c),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
