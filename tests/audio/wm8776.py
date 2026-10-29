#!/usr/bin/env python3
"""Exercise the production codec initialization and every volume level."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);test=p/'test.c'
 test.write_text(r'''
#define _GNU_SOURCE
#define MACHINE_A2560M
#include <sys/mman.h>
#include <assert.h>
#include <stdio.h>
#include "wm8776.c"
int main(void) {
 unsigned v;uint16_t last=0;
 void *mapping=mmap((void *)0xfec20000UL,65536,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
 assert(mapping!=(void *)-1);
 wm8776_init();
 assert(wm8776_regs[13]==0 && wm8776_regs[21]==31 && wm8776_regs[22]==7);
 assert(wm8776_get_digital_volume()==255 && wm8776_regs[5]==0x1ff && wm8776_regs[2]==0x179);
 for(v=0;v<=255;v++) {
  wm8776_set_digital_volume(v);
  assert(wm8776_get_digital_volume()==v);
  assert(wm8776_regs[5]==(0x100|v));
  assert(wm8776_regs[2]&0x100);
  assert((wm8776_regs[2]&0x7f)>=last && (wm8776_regs[2]&0x7f)<=0x79);
  last=wm8776_regs[2]&0x7f;
  assert(*wm8776==(0x400|wm8776_regs[2]));
 }
 wm8776_set_digital_volume(0);assert(wm8776_regs[2]==0x12f && wm8776_regs[5]==0x100);
 munmap(mapping,65536);
 puts("PASS: WM8776 boot route, unity initialization, UPDATE latches, mute and all 256 volume round trips");
}
''')
 subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-Wno-sign-compare','-I'+str(ROOT/'foenix'),str(test),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
