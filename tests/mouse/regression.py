#!/usr/bin/env python3
"""Exercise the production A2560Me three-byte PS/2 packet parser.

Distributed under GPL version 2 or later; see doc/license.txt.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'foenix/ps2_mouse_a2560.c').read_text()
start = source.index('void process(struct ps2_driver_api_t *api, uint8_t byte)\n{')
function = source[start:]
prefix = r'''
#include <stdint.h>
#include <assert.h>
#include <string.h>
#include <stdio.h>
#define MACHINE_A2560M 1
#define MAXIMUM_TOS_COMPATIBILITY 0
#define SM_IDLE 0
#define SM_RECEIVED 3
struct ps2_driver_api_t {
    struct { void (*on_mouse)(uint8_t *); } callbacks;
    uint32_t driver_data;
};
struct __attribute__((packed)) ps2_mouse_local_t {
    uint8_t packet[3];
    uint8_t state;
};
#define DRIVER_DATA ((struct ps2_mouse_local_t*)&api->driver_data)
static unsigned calls;
static uint8_t last[3];
static void receive(uint8_t *packet)
{
    calls++;
    memcpy(last, packet, 3);
    /* The actual IKBD adapter modifies the packet in place. */
    packet[0] = 0xfa;
}
'''
test = r'''
int main(void)
{
    struct ps2_driver_api_t api = {{receive}, 0};
    unsigned i;
    /* Stray non-header bytes must not synthesize a button event. */
    for (i = 0; i < 12; i++) process(&api, 0);
    assert(calls == 0);
    /* Bit 3 is required only on the header, not on motion bytes. */
    process(&api, 0x09); process(&api, 0x08); process(&api, 0xff);
    assert(calls == 1 && last[0] == 0x09 && last[1] == 8 && last[2] == 255);
    process(&api, 0x08); process(&api, 0); process(&api, 0);
    assert(calls == 2 && (last[0] & 3) == 0);
    /* Lost byte: the following packet can be malformed; framing must
     * recover at a later valid header rather than remaining shifted. */
    process(&api, 0x09); process(&api, 0); /* one motion byte lost */
    process(&api, 0x08); process(&api, 0); process(&api, 0);
    assert(calls == 3);
    process(&api, 0x08); process(&api, 0); process(&api, 0);
    assert(calls == 4 && last[0] == 0x08 && last[1] == 0 && last[2] == 0);
    puts("PASS: stray bytes rejected, press/release packets, motion bytes, framing recovery");
}
'''
with tempfile.TemporaryDirectory(prefix='mouse-regression-') as directory:
    c = Path(directory) / 'test.c'
    exe = Path(directory) / 'test'
    c.write_text(prefix + function + test)
    subprocess.run(['cc', '-std=c99', '-fsanitize=address,undefined',
                    str(c), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
