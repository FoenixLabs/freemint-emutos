/* Cache-coherent DDR VDMA diagnostic, outside the live framebuffer.
 * GPL-2.0-or-later. */
#include <stdint.h>
#include <string.h>
void *memcpy(void *dst, const void *src, size_t size)
{
    unsigned char *d=dst;
    const unsigned char *s=src;
    while(size--) *d++=*s++;
    return dst;
}
#include <mint/osbind.h>
#include "a2560me_memory.h"
#define ME_RENDERING
#include "cache.h"
#include "dma.h"
#define SCRATCH (A2560ME_VIDEO_BASE + 4UL*1024*1024)
static long cache_test(void)
{
    volatile uint16_t *a=(volatile uint16_t *)SCRATCH;
    volatile uint16_t *b=(volatile uint16_t *)(SCRATCH+65536);
    struct me_dma_rect src={SCRATCH,512,256,128};
    struct me_dma_rect dst={SCRATCH+65536,512,256,128};
    uint32_t c,d0,d1,i;
    long result=0;
    /* Only documented A2560Me firmware owns this reserved scratch space. */
    const uint32_t *jar=*(const uint32_t * volatile *)0x5a0;
    short cpu=0, machine=0, reservation=0;
    while (jar && jar[0])
    {
        if (jar[0]==0x5f435055UL && jar[1]==60) cpu=1;
        if (jar[0]==0x5f4d4348UL && jar[1]==0xf258) machine=1;
        if (jar[0]==A2560ME_VIDEO_COOKIE && jar[1]==A2560ME_VIDEO_BASE) reservation=1;
        jar+=2;
    }
    if (!cpu || !machine || !reservation || !me_cache_available()) return 0;
    __asm__ volatile ("movec %%dtt0,%0\n\tmovec %%dtt1,%1" : "=d"(d0),"=d"(d1));
    c=me_disable_dcache();
    me_render_cache();
    for(i=0;i<32768;i++) { a[i]=(uint16_t)(i^0x5aa5); b[i]=0xdead; }
    /* Prime destination cache lines, then verify DMA invalidation. */
    for(i=0;i<32768;i++) if(b[i]!=0xdead) goto out;
    if(me_dma_run(&src,&dst,0)!=1) goto out;
    for(i=0;i<32768;i++) if(b[i]!=(uint16_t)(i^0x5aa5)) goto out;
    if(me_dma_run(0,&dst,0x07e0)!=1) goto out;
    for(i=0;i<32768;i++) if(b[i]!=0x07e0) goto out;
    src.width=dst.width=200; src.height=dst.height=100;
    dst.address=SCRATCH+512+16;
    if(me_dma_run(&src,&dst,0)!=1) goto out;
    for(i=0;i<100;i++)
    {
        uint32_t x;
        for(x=0;x<200;x++) if(a[(i+1)*256+8+x]!=(uint16_t)((i*256+x)^0x5aa5)) goto out;
    }
    src.address=dst.address; dst.address=SCRATCH;
    if(me_dma_run(&src,&dst,0)!=1) goto out;
    for(i=0;i<100;i++)
    {
        uint32_t x;
        for(x=0;x<200;x++) if(a[i*256+x]!=(uint16_t)((i*256+x)^0x5aa5)) goto out;
    }
    result=1;
out:
    (void)me_disable_dcache();
    __asm__ volatile ("movec %0,%%dtt0\n\tmovec %1,%%dtt1" : : "d"(d0),"d"(d1) : "memory");
    me_restore_dcache(c);
    return result;
}
long probe_main(void);
long probe_main(void)
{
    (void)Cconws("A2560Me cache + VDMA test (reserved off-screen DDR).\r\n");
    if (!Supexec(cache_test))
    {
        (void)Cconws("FAIL: firmware compatibility, cache coherence, DMA or overlap check.\r\n");
        return 1;
    }
    (void)Cconws("PASS: cached CPU writes, VDMA copy/fill, cached readback, both overlap directions.\r\n");
    return 0;
}
