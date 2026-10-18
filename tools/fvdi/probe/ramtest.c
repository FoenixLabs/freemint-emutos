/* Test alternate-RAM allocation without touching the video reservation.
 * GPL-2.0-or-later. */
#include <stdint.h>
#include <mint/osbind.h>
#include <mint/mintbind.h>
#include "a2560me_memory.h"

#define SAMPLE_SIZE (4UL * 1024 * 1024)
static void hex(uint32_t value)
{
    static const char digits[] = "0123456789ABCDEF";
    char text[11];
    short i;
    text[0] = '0'; text[1] = 'x'; text[10] = 0;
    for (i = 9; i >= 2; i--)
    {
        text[i] = digits[value & 15];
        value >>= 4;
    }
    (void)Cconws(text);
}
long probe_main(void);
long probe_main(void)
{
    uint32_t address, i;
    volatile uint32_t *p;
    long largest = (long)Mxalloc(-1L, 1);
    (void)Cconws("Largest alternate-RAM block: "); hex(largest); (void)Cconws("\r\n");
    if (largest < (long)SAMPLE_SIZE)
    {
        (void)Cconws("FAIL: not enough alternate RAM.\r\n");
        return 1;
    }
    p = (volatile uint32_t *)Mxalloc(SAMPLE_SIZE, 1);
    address = (uint32_t)p;
    if (!p || (long)p < 0)
        return 1;
    if (address < A2560ME_DDR_BASE || address > A2560ME_VIDEO_BASE - SAMPLE_SIZE)
    {
        (void)Cconws("FAIL: allocation outside DDR RAM pool.\r\n");
        (void)Mfree((void *)p);
        return 1;
    }
    (void)Cconws("Testing 4 MiB at "); hex(address); (void)Cconws("\r\n");
    for (i = 0; i < SAMPLE_SIZE / 4; i++)
        p[i] = (i * 0x9e3779b9UL) ^ 0xa2560060UL;
    for (i = 0; i < SAMPLE_SIZE / 4; i++)
    {
        if (p[i] != ((i * 0x9e3779b9UL) ^ 0xa2560060UL))
        {
            (void)Cconws("FAIL at "); hex(address + 4*i); (void)Cconws("\r\n");
            (void)Mfree((void *)p);
            return 1;
        }
    }
    (void)Mfree((void *)p);
    (void)Cconws("PASS: alternate-RAM allocation, reservation bounds and 4 MiB pattern.\r\n");
    return 0;
}
