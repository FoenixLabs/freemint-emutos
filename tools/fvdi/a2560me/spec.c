/*
 * A2560Me RGB565 fVDI driver, derived from Johan Klockars's public-domain
 * 16-bit driver example. GPL version 2 or later; see LICENSE.TXT.
 * Copyright (C) 2026 The EmuTOS development team
 */
#include "fvdi.h"
#include "driver.h"
#include "relocate.h"
#include "../bitplane/bitplane.h"
#include "os.h"
#include "string/memset.h"
#include "video.h"
#define ME_RENDERING
#include "cache.h"
#include "dma.h"

/* XaAES may restore CACR around v_opnwk. Reassert the write-through
 * RAM mappings and D-cache enable at each entry, without flushing when
 * already configured. DMA alone needs cache synchronization. */
static short dma_disabled;
static int dma_result(int result)
{
    if (result < 0)
    {
        dma_disabled = 1;
        access->funcs.puts("A2560Me: VDMA error/timeout; acceleration disabled.\r\n");
    }
    return result != 0;
}
static int me_rect(Workstation *wk, MFDB *m, long x, long y, long w, long h,
    struct me_dma_rect *r)
{
    long width, height;
    if (!m || !m->address || m->address == wk->screen.mfdb.address)
    {
        r->address = (uint32_t)wk->screen.mfdb.address;
        r->stride = wk->screen.wrap;
        width = wk->screen.mfdb.width; height = wk->screen.mfdb.height;
    }
    else
    {
        if (m->bitplanes != 16 || m->standard || m->wdwidth <= 0)
            return 0;
        r->address = (uint32_t)m->address;
        r->stride = (uint32_t)m->wdwidth * 32;
        width = m->width; height = m->height;
    }
    if (x < 0 || y < 0 || w <= 0 || h <= 0 || x > width - w || y > height - h ||
        r->address < A2560ME_DDR_BASE || r->address >= A2560ME_DDR_TOP ||
        r->stride < (uint32_t)width * 2 || r->stride > A2560ME_DDR_TOP ||
        (uint32_t)y > (A2560ME_DDR_TOP - r->address) / r->stride)
        return 0;
    r->address += (uint32_t)y * r->stride;
    if ((uint32_t)x * 2 > A2560ME_DDR_TOP - r->address)
        return 0;
    r->address += x * 2;
    r->width = w; r->height = h;
    return me_dma_valid(r);
}
static long CDECL me_write_pixel(Virtual *v, MFDB *m, long x, long y, long c)
{ me_render_cache(); return c_write_pixel(v,m,x,y,c); }
static long CDECL me_read_pixel(Virtual *v, MFDB *m, long x, long y)
{ me_render_cache(); return c_read_pixel(v,m,x,y); }
static long CDECL me_line(Virtual *v, long x1,long y1,long x2,long y2,long p,long c,long m)
{ me_render_cache(); return c_line_draw(v,x1,y1,x2,y2,p,c,m); }
static long CDECL me_fill(Virtual *v,long x,long y,long w,long h,short *p,long c,long m,long s)
{
    struct me_dma_rect dst;
    unsigned long fg, bg;
    short i;
    me_render_cache();
    if (!dma_disabled && !((long)v & 1) && m == 1 && w >= 16 && h > 0 &&
        p && me_rect(v->real_address, 0, x,y,w,h,&dst) &&
        (uint32_t)w * (uint32_t)h >= 1024)
    {
        for (i = 0; i < 16 && (unsigned short)p[i] == 0xffff; i++) { }
        if (i == 16)
        {
            c_get_colours(v,c,&fg,&bg);
            if (dma_result(me_dma_run(0,&dst,(uint16_t)fg)))
                return 1;
        }
    }
    return c_fill_area(v,x,y,w,h,p,c,m,s);
}
static long CDECL me_expand(Virtual *v,MFDB *s,long sx,long sy,MFDB *d,long dx,long dy,long w,long h,long m,long c)
{ me_render_cache(); return c_expand_area(v,s,sx,sy,d,dx,dy,w,h,m,c); }
static long CDECL me_blit(Virtual *v,MFDB *s,long sx,long sy,MFDB *d,long dx,long dy,long w,long h,long m)
{
    struct me_dma_rect src, dst;
    me_render_cache();
    if (!dma_disabled && !((long)v & 1) && m == 3 && w >= 16 && h > 0 &&
        me_rect(v->real_address,s,sx,sy,w,h,&src) &&
        me_rect(v->real_address,d,dx,dy,w,h,&dst) &&
        (uint32_t)w * (uint32_t)h >= 1024 && dma_result(me_dma_run(&src,&dst,0)))
        return 1;
    return c_blit_area(v,s,sx,sy,d,dx,dy,w,h,m);
}
static long CDECL me_mouse(Workstation *w,long x,long y,Mouse *m)
{ me_render_cache(); return c_mouse_draw(w,x,y,m); }

static char const r_16[] = { 5, 11, 12, 13, 14, 15 };
static char const g_16[] = { 6,  5,  6,  7,  8,  9, 10 };
static char const b_16[] = { 5,  0,  1,  2,  3,  4 };
static char const none[] = { 0 };

#if 0
static char const red[] = { 5, 11, 12, 13, 14, 15 };
static char const green[] = { 5, 6, 7, 8, 9, 10 };
static char const blue[] = { 5, 0, 1, 2, 3, 4 };
static char const alpha[] = { 0 };
static char const genlock[] = { 0 };
static char const unused[] = { 1, 5 };
#endif

static Mode const mode[1] = {
    { 16, CHUNKY | TRUE_COLOUR, { r_16, g_16, b_16, none, none, none }, 0, 2, 2, 1 }
};

char driver_name[] = "A2560Me RGB565 DDR3";

long CDECL (*write_pixel_r)(Virtual *vwk, MFDB *mfdb, long x, long y, long colour) = me_write_pixel;
long CDECL (*read_pixel_r)(Virtual *vwk, MFDB *mfdb, long x, long y) = me_read_pixel;
long CDECL (*line_draw_r)(Virtual *vwk, long x1, long y1, long x2, long y2, long pattern, long colour, long mode) = me_line;
long CDECL (*expand_area_r)(Virtual *vwk, MFDB *src, long src_x, long src_y, MFDB *dst, long dst_x, long dst_y, long w, long h, long operation, long colour) = me_expand;
long CDECL (*fill_area_r)(Virtual *vwk, long x, long y, long w, long h, short *pattern, long colour, long mode, long interior_style) = me_fill;
long CDECL (*fill_poly_r)(Virtual *vwk, short points[], long n, short index[], long moves, short *pattern, long colour, long mode, long interior_style) = 0;
long CDECL (*blit_area_r)(Virtual *vwk, MFDB *src, long src_x, long src_y, MFDB *dst, long dst_x, long dst_y, long w, long h, long operation) = me_blit;
long CDECL (*text_area_r)(Virtual *vwk, short *text, long length, long dst_x, long dst_y, short *offsets) = 0;
long CDECL (*mouse_draw_r)(Workstation *wk, long x, long y, Mouse *mouse) = me_mouse;

long CDECL (*get_colour_r)(Virtual *vwk, long colour) = c_get_colour;
void CDECL (*get_colours_r)(Virtual *vwk, long colour, unsigned long *foreground, unsigned long *background) = 0;
void CDECL (*set_colours_r)(Virtual *vwk, long start, long entries, unsigned short *requested, Colour palette[]) = c_set_colours;

long wk_extend = 0;
short accel_s = 0;
short accel_c = A_SET_PAL | A_GET_COL | A_SET_PIX | A_GET_PIX | A_BLIT | A_FILL | A_EXPAND | A_LINE | A_MOUSE;

const Mode *graphics_mode = &mode[0];

short fix_shape = 0;
short no_restore = 0;


static struct me_video_state video_state;
static short half_mode;
static short board_ready;
static uint32_t initial_cache, initial_dtt0, initial_dtt1;

/* VDI calls run in supervisor mode; initialization may run from user mode. */
static long validate_video(void)
{
    __asm__ volatile ("movec %%cacr,%0\n\tmovec %%dtt0,%1\n\tmovec %%dtt1,%2"
        : "=d"(initial_cache), "=d"(initial_dtt0), "=d"(initial_dtt1));
    return me_cache_available() && me_video_available();
}

long check_token(char *token, const char **ptr)
{
    (void)ptr;
    if (!video_state.active && access->funcs.equal(token, "half"))
    {
        half_mode = 1;
        return 1;
    }
    return 0;
}

static void describe_screen(Workstation *wk)
{
    wk->screen.mfdb.width = half_mode ? 640 : 1280;
    wk->screen.mfdb.height = me_height(half_mode);
    wk->screen.mfdb.bitplanes = 16;
    wk->screen.mfdb.wdwidth = wk->screen.mfdb.width / 16;
    wk->screen.mfdb.address = (void *)A2560ME_VIDEO_BASE;
    wk->screen.mfdb.standard = 0;
    wk->screen.wrap = wk->screen.mfdb.width * 2;
    wk->screen.shadow.buffer = 0;
    wk->screen.shadow.address = 0;
    wk->screen.shadow.wrap = 0;
    wk->screen.coordinates.min_x = wk->screen.coordinates.min_y = 0;
    wk->screen.coordinates.max_x = wk->screen.mfdb.width - 1;
    wk->screen.coordinates.max_y = wk->screen.mfdb.height - 1;
    wk->screen.look_up_table = 0;
    device.byte_width = wk->screen.wrap;
    device.address = wk->screen.mfdb.address;
}

long CDECL initialize(Virtual *vwk)
{
    Workstation *wk;
    Colour *palette;
    long cookie;
    (void)vwk;
    if (access->funcs.get_cookie("_MCH", 0) != 0x0000f258L ||
        access->funcs.get_cookie("_CPU", 0) != 60)
        return 0;
    cookie = access->funcs.get_cookie("FVRM", 0);
    if (cookie != (long)A2560ME_VIDEO_BASE)
    {
        access->funcs.puts("A2560Me: compatible DDR/framebuffer reservation firmware required.\r\n");
        return 0;
    }
    if (!Supexec(validate_video))
    {
        access->funcs.puts("A2560Me: MMU active, endian inversion or GGE active; bitmap mode refused.\r\n");
        return 0;
    }
    palette = access->funcs.malloc(256L * sizeof(Colour), 3);
    if (!palette)
        return 0;
    vwk = me->default_vwk;
    wk = vwk->real_address;
    wk->screen.palette.size = 256;
    wk->screen.palette.colours = palette;
    describe_screen(wk);
    wk->screen.pixel.width = 264;  /* approximately 96 dpi */
    wk->screen.pixel.height = 264;
    c_initialize_palette(vwk, 0, 256, default_vdi_colors, palette);
    wk->mouse.position.x = wk->screen.mfdb.width / 2;
    wk->mouse.position.y = wk->screen.mfdb.height / 2;
    board_ready = 1;
    access->funcs.puts("A2560Me fVDI: RGB565 in reserved DDR3; write-through CPU cache + VDMA copy/fill.\r\n");
    return 1;
}

long CDECL setup(long type, long value)
{
    switch (type)
    {
    case Q_NAME: return (long)driver_name;
    case S_DRVOPTION: return tokenize((char *)value);
    }
    return -1;
}

Virtual *CDECL opnwk(Virtual *vwk)
{
    (void)vwk;
    if (board_ready)
    {
        describe_screen(me->default_vwk->real_address);
        if (me_video_enter(&video_state, half_mode))
            {
            video_state.cache = initial_cache;
            me_render_cache();
        }
    }
    return 0;
}

void CDECL clswk(Virtual *vwk)
{
    uint16_t sr;
    (void)vwk;
    if (!video_state.active)
        return;
    sr = me_dma_lock();
    __asm__ volatile ("movec %0,%%dtt0\n\tmovec %1,%%dtt1"
        : : "d"(initial_dtt0), "d"(initial_dtt1) : "memory");
    me_video_leave(&video_state);
    me_dma_unlock(sr);
}
