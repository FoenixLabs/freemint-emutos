/* A2560Me GUI bitmap transitions; GPL-2.0-or-later. */
#ifndef A2560ME_VIDEO_H
#define A2560ME_VIDEO_H
#include <stdint.h>
#include "a2560me_memory.h"

#define ME_MASTER       0xfec80000UL
#define ME_BORDER       0xfec80004UL
#define ME_MOUSE        0xfec80c00UL
#define ME_GUI          0xfc000000UL
#define ME_GAVIN        0xfec00000UL
#define ME_GGE          0xfd000000UL
#define ME_TOSGRAPH     0x00100000UL
#define ME_MEMTEXT      0x00004000UL
#define ME_GRAPHICS     0x00000004UL
#define ME_VIDEO1024    0x00000100UL

#ifndef ME_R32
#define ME_R32(a) (*(volatile uint32_t *)(a))
#define ME_R16(a) (*(volatile uint16_t *)(a))
#endif

#ifndef ME_PIXELS
#define ME_PIXELS ((volatile uint32_t *)A2560ME_VIDEO_BASE)
#endif

struct me_video_state {
    uint32_t master, border, gui_ctrl, gui_addr, gui_stride, mono, mono_bg;
    uint32_t cache;
    uint16_t mouse;
    short active;
};

/* Supplied by target assembly, or by the host test's cache model. */
static uint32_t me_disable_dcache(void);
static void me_restore_dcache(uint32_t saved);

static unsigned short me_height(unsigned short half)
{
    unsigned short height = (ME_R32(ME_MASTER) & ME_VIDEO1024) ? 1024 : 960;
    return half ? height / 2 : height;
}

static int me_video_available(void)
{
    /* Never change global DDR byte order or steal a running GGE's port. */
    return !(ME_R32(ME_GAVIN) & 0x40UL) && !(ME_R32(ME_GGE) & 1UL);
}

static int me_video_enter(struct me_video_state *s, unsigned short half)
{
    volatile uint32_t *pixels;
    uint32_t count;
    if (s->active)
        return 1;
    if (!me_video_available())
        return 0;
    s->master = ME_R32(ME_MASTER);
    s->border = ME_R32(ME_BORDER);
    s->mouse = ME_R16(ME_MOUSE);
    s->gui_ctrl = ME_R32(ME_GUI);
    s->gui_addr = ME_R32(ME_GUI + 4);
    s->mono = ME_R32(ME_GUI + 8);
    s->gui_stride = ME_R32(ME_GUI + 12);
    s->mono_bg = ME_R32(ME_GUI + 16);
    s->cache = me_disable_dcache();
    pixels = ME_PIXELS;
    count = (uint32_t)(half ? 640 : 1280) * me_height(half) / 2;
    while (count--)
        *pixels++ = 0;
    ME_R32(ME_GUI) = 0;
    /* ADDR takes a byte address, not an address divided by four or 32. */
    ME_R32(ME_GUI + 4) = A2560ME_VIDEO_BASE;
    ME_R32(ME_GUI + 12) = half ? 1280 : 2560;
    ME_R16(ME_MOUSE) = s->mouse & ~1U;
    ME_R32(ME_BORDER) = 0;
    ME_R32(ME_GUI) = half ? 5 : 13; /* enabled, RGB565, 640 or 1280 */
    ME_R32(ME_MASTER) = (s->master & ~(ME_TOSGRAPH | ME_MEMTEXT |
        0x00001403UL)) | ME_GRAPHICS;
    s->active = 1;
    return 1;
}

static void me_video_leave(struct me_video_state *s)
{
    if (!s->active)
        return;
    ME_R32(ME_GUI) = 0;
    ME_R32(ME_GUI + 4) = s->gui_addr;
    ME_R32(ME_GUI + 8) = s->mono;
    ME_R32(ME_GUI + 12) = s->gui_stride;
    ME_R32(ME_GUI + 16) = s->mono_bg;
    ME_R32(ME_GUI) = s->gui_ctrl;
    ME_R32(ME_BORDER) = s->border;
    ME_R32(ME_MASTER) = s->master;
    ME_R16(ME_MOUSE) = s->mouse;
    me_restore_dcache(s->cache);
    s->active = 0;
}
#endif
