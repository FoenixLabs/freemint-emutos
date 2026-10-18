/* 68060 data-cache transitions; GPL-2.0-or-later. */
#ifndef A2560ME_CACHE_H
#define A2560ME_CACHE_H
#include <stdint.h>
static uint32_t me_disable_dcache(void)
{
    uint32_t saved, disabled;
    uint16_t sr;
    __asm__ volatile ("move.w %%sr,%1\n\tori.w #0x0700,%%sr\n\tmovec %%cacr,%0"
        : "=d"(saved), "=d"(sr) : : "cc", "memory");
    if (saved & 0x80000000UL)
    {
        disabled = saved & 0x7fffffffUL;
        __asm__ volatile ("cpusha %%dc\n\tcinva %%dc\n\tmovec %0,%%cacr" : : "d"(disabled) : "cc", "memory");
    }
    __asm__ volatile ("move.w %0,%%sr" : : "d"(sr) : "cc", "memory");
    return saved;
}

static void me_restore_dcache(uint32_t saved)
{
    uint32_t current;
    uint16_t sr;
    __asm__ volatile ("move.w %%sr,%1\n\tori.w #0x0700,%%sr\n\tmovec %%cacr,%0"
        : "=d"(current), "=d"(sr) : : "cc", "memory");
    current = (current & 0x7fffffffUL) | (saved & 0x80000000UL);
    __asm__ volatile ("cpusha %%dc\n\tcinva %%dc\n\tmovec %0,%%cacr\n\tmove.w %1,%%sr"
        : : "d"(current), "d"(sr) : "cc", "memory");
}
#ifdef ME_RENDERING
/* Cache RAM write-through in both privilege modes. MMIO is inhibited by
 * the FPGA's TCI signal; retain an explicit inhibited high-I/O TTR too.
 * The driver saves/restores the original mappings at workstation lifetime.
 */
static int me_cache_available(void)
{
    uint32_t tc;
    __asm__ volatile ("movec %%tc,%0" : "=d"(tc));
    return !(tc & 0x8000UL);
}
static void me_render_cache(void)
{
    uint32_t d0, d1, c;
    __asm__ volatile ("movec %%dtt0,%0\n\tmovec %%dtt1,%1\n\tmovec %%cacr,%2"
        : "=d"(d0), "=d"(d1), "=d"(c) : : "memory");
    if (d0 != 0x003fe000UL || d1 != 0xc03fe040UL || !(c & 0x80000000UL))
    {
        uint16_t sr;
        __asm__ volatile ("move.w %%sr,%0\n\tori.w #0x0700,%%sr\n\tcpusha %%dc"
            : "=d"(sr) : : "cc", "memory");
        d0 = 0x003fe000UL; d1 = 0xc03fe040UL; c |= 0x80000000UL;
        __asm__ volatile ("movec %0,%%dtt0\n\tmovec %1,%%dtt1\n\tmovec %2,%%cacr\n\tmove.w %3,%%sr"
            : : "d"(d0), "d"(d1), "d"(c), "d"(sr) : "cc", "memory");
    }
}

static uint16_t me_dma_lock(void)
{
    uint16_t sr;
    __asm__ volatile ("move.w %%sr,%0\n\tori.w #0x0700,%%sr\n\tcpusha %%dc"
        : "=d"(sr) : : "cc", "memory");
    return sr;
}
static void me_dma_unlock(uint16_t sr)
{
    __asm__ volatile ("cinva %%dc\n\tmove.w %0,%%sr" : : "d"(sr) : "cc", "memory");
}
#endif
#endif
