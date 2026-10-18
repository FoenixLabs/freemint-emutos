/* Synchronous A2560Me DDR3 VDMA copy/fill; GPL-2.0-or-later.
 * Hardware Reference rev 1.8, pp. 84-87. Longword MMIO only.
 */
#ifndef A2560ME_DMA_H
#define A2560ME_DMA_H
#include <stdint.h>
#include "a2560me_memory.h"
#define ME_VDMA 0xfec0c200UL
#ifndef ME_DMA_R
#define ME_DMA_R(offset) (*(volatile uint32_t *)(ME_VDMA + (offset)))
#endif
#ifndef ME_DMA_START
#define ME_DMA_START() (ME_DMA_R(0) = 2)
#define ME_DMA_ABORT() (ME_DMA_R(0) = 4)
#endif
/* Bounded poll; no IRQ completion or timer dependency while IPL7 is held. */
#define ME_DMA_POLLS 200000UL
struct me_dma_rect { uint32_t address, stride, width, height; };

static int me_dma_valid(const struct me_dma_rect *r)
{
    uint32_t line, last;
    if (!r->width || !r->height || r->width > 65535UL || r->height > 65535UL ||
        (r->address & 1) || (r->stride & 1) || r->address < A2560ME_DDR_BASE ||
        r->address >= A2560ME_DDR_TOP)
        return 0;
    line = r->width * 2;
    if (r->stride < line || r->stride > A2560ME_DDR_TOP ||
        r->height - 1 > (A2560ME_DDR_TOP - r->address) / r->stride)
        return 0;
    last = r->address + (r->height - 1) * r->stride;
    return line <= A2560ME_DDR_TOP - last;
}

/* 1 completed, 0 not started (CPU fallback), -1 failed (disable DMA).
 * Copy/fill are idempotent except overlapping copies, so never replay a
 * failed operation through the CPU: it may have already moved segments.
 */
static int me_dma_run(const struct me_dma_rect *src,
    const struct me_dma_rect *dst, uint16_t colour)
{
    uint32_t ctrl = 0x1f0UL, sa = 0, ss = 0, da, ds, n, status;
    uint16_t sr;
    if (!me_dma_valid(dst) || (src && (!me_dma_valid(src) ||
        src->width != dst->width || src->height != dst->height)))
        return 0;
    sr = me_dma_lock();
    if (ME_DMA_R(4) & 1)
    {
        me_dma_unlock(sr);
        return 0;
    }
    da = dst->address; ds = dst->stride;
    if (src)
    {
        sa = src->address; ss = src->stride;
        ctrl |= 0x800;
        /* Overlap-safe for identical raster layout. With different wraps,
         * leave potentially overlapping buffers to the generic renderer. */
        if (sa != da && sa < da &&
            da < sa + (src->height - 1) * ss + src->width * 2)
        {
            if (ss != ds)
            {
                me_dma_unlock(sr);
                return 0;
            }
            sa += (src->height - 1) * ss;
            da += (dst->height - 1) * ds;
            ss = 0UL - ss; ds = 0UL - ds;
            ctrl |= 0x20000UL;
        }
    }
    ME_DMA_R(0x40) = ctrl;
    ME_DMA_R(0x44) = (dst->height << 16) | dst->width;
    ME_DMA_R(0x48) = sa; ME_DMA_R(0x4c) = ss;
    ME_DMA_R(0x50) = 0; ME_DMA_R(0x54) = 0;
    ME_DMA_R(0x58) = 0; ME_DMA_R(0x5c) = 0;
    ME_DMA_R(0x60) = da; ME_DMA_R(0x64) = ds;
    ME_DMA_R(0x68) = colour;
    ME_DMA_R(0x6c) = 0; ME_DMA_R(0x70) = 0;
    ME_DMA_R(0x74) = 0; ME_DMA_R(0x78) = 0; ME_DMA_R(0x7c) = 0;
    ME_DMA_R(4) = 6; /* W1C stale completion/error before issuing START. */
    ME_DMA_START();
    status = 0;
    for (n = ME_DMA_POLLS; n; n--)
    {
        status = ME_DMA_R(4);
        if ((status & 6) && !(status & 1))
            break;
    }
    if (!n || !(status & 2) || (status & 4))
    {
        ME_DMA_ABORT();
        for (n = ME_DMA_POLLS; n && (ME_DMA_R(4) & 1); n--) { }
        me_dma_unlock(sr);
        return -1;
    }
    me_dma_unlock(sr);
    return 1;
}
#endif
