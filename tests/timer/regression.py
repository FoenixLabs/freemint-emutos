#!/usr/bin/env python3
"""Check the production calibration function's vector save/restore addresses.

MMIO is modelled as cells indexed by byte address; no hardware is accessed.
Distributed under GPL version 2 or later; see doc/license.txt.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, default=root / 'foenix/timer.c')
args = parser.parse_args()
source = args.source.read_text()
start = source.index('uint32_t a2560_delay_calibrate(uint32_t calibration_time)')
# This is the final function in timer.c.
function = source[start:]
prefix = r'''
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <stdio.h>
#define IRQ_GROUPS 3
#define INT_TIMER0_VECN 0x51
#define a2560_debugnl(...) ((void)0)
static uint32_t registers[1024];
#define R32(address) registers[(address)]
static void a2560_irq_calibration(void) {}
static void a2560_irq_mask_all(uint16_t *masks)
{
    unsigned i;
    for (i = 0; i < IRQ_GROUPS; i++) masks[i] = 0xff00 + i;
}
static void a2560_irq_restore(const uint16_t *masks)
{
    unsigned i;
    for (i = 0; i < IRQ_GROUPS; i++) assert(masks[i] == 0xff00 + i);
}
static void a2560_set_timer(uint16_t timer, uint32_t frequency,
                           bool repeat, void (*handler)(void))
{
    assert(timer == 0 && frequency == 10 && !repeat);
    assert(handler == a2560_irq_calibration);
    R32(INT_TIMER0_VECN * 4) = 0x0013b854;
}
static void a2560_timer_enable(uint16_t timer, bool enable)
{
    assert(timer == 0 && enable);
}
static uint32_t a2560_run_calibration(uint32_t milliseconds)
{
    assert(milliseconds == 100);
    return 2500000;
}
'''
test = r'''
int main(void)
{
    unsigned i;
    for (i = 0; i < 1024; i++) registers[i] = 0xdead0000 + i;
    R32(INT_TIMER0_VECN * 4) = 0x0013b6f2;
    assert(a2560_delay_calibrate(100) == 25000);
    assert(R32(INT_TIMER0_VECN * 4) == 0x0013b6f2);
    for (i = 0; i < 1024; i++)
        if (i != INT_TIMER0_VECN * 4)
            assert(registers[i] == 0xdead0000 + i);
    puts("PASS: calibration restores vector at 0x144 and leaves other addresses untouched");
}
'''
with tempfile.TemporaryDirectory(prefix='timer-regression-') as directory:
    c = Path(directory) / 'test.c'
    exe = Path(directory) / 'test'
    c.write_text(prefix + function + test)
    subprocess.run(['cc', '-std=c99', '-g', '-fsanitize=address,undefined',
                    str(c), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
