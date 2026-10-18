#!/usr/bin/env python3
"""Exercise the production PS/2 adapter through a replaced TOS keyboard vector.

Distributed under GPL version 2 or later; see doc/license.txt.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / "bios/a2560_bios.c").read_text()
start = source.index("static void ps2_to_ikbd_key_adapter(uint8_t scancode)\n{")
end = source.index("\n#endif", start)
function = source[start:end]
harness = r'''
#include <stdint.h>
#include <assert.h>
#include <stdio.h>
typedef uint8_t UBYTE;
static unsigned calls;
static UBYTE last;
static void receive(UBYTE code) { calls++; last = code; }
static void (*kbdvec)(UBYTE) = receive;
static void call_kbdvec(UBYTE code) { kbdvec(code); }
'''
tests = r'''
static void check(unsigned pc, unsigned atari)
{
    unsigned before = calls;
    ps2_to_ikbd_key_adapter(pc);
    assert(calls == before + 1 && last == atari);
    ps2_to_ikbd_key_adapter(pc | 0x80);
    assert(calls == before + 2 && last == (atari | 0x80));
}
static void replacement(UBYTE code) { calls += 10; last = code; }
int main(void)
{
    unsigned i, before;
    /* Ordinary typing/modifiers must retain the TOS key numbers. */
    for (i = 1; i <= 0x36; ++i) check(i, i);
    for (i = 0x38; i <= 0x44; ++i) check(i, i);
    check(103, 0x48); check(105, 0x4b); check(106, 0x4d);
    check(108, 0x50); check(102, 0x47); check(110, 0x52);
    check(111, 0x53); check(104, 0x49); check(109, 0x51);
    check(107, 0x4f); check(87, 0x62); check(88, 0x61);
    check(71, 0x67); check(72, 0x68); check(73, 0x69);
    check(75, 0x6a); check(76, 0x6b); check(77, 0x6c);
    check(79, 0x6d); check(80, 0x6e); check(81, 0x6f);
    check(82, 0x70); check(83, 0x71); check(96, 0x72);
    check(55, 0x66); check(98, 0x65); check(74, 0x4a);
    check(78, 0x4e); check(86, 0x60);
    check(97, 0x1d); check(100, 0x38);
    before = calls;
    ps2_to_ikbd_key_adapter(0); ps2_to_ikbd_key_adapter(0x80);
    ps2_to_ikbd_key_adapter(69); ps2_to_ikbd_key_adapter(69 | 0x80);
    ps2_to_ikbd_key_adapter(127);
    assert(calls == before);
    /* Replacing the vector must immediately redirect subsequent events. */
    kbdvec = replacement;
    ps2_to_ikbd_key_adapter(103);
    assert(calls == before + 10 && last == 0x48);
    puts("PS/2 -> TOS keyboard-vector regression passed");
    return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp) / "keyboard.c"
    exe = Path(tmp) / "keyboard"
    c.write_text(harness + function + tests)
    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                    str(c), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
