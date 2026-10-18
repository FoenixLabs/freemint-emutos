/* RGB565 scanout test from the FreeMiNT recovery shell; GPL-2.0-or-later. */
#include <stdint.h>
#include <mint/osbind.h>
#include "video.h"
#include "cache.h"

static struct me_video_state state;
static long pattern(void)
{
    static const uint16_t colours[8] = {
        0xffff, 0xffe0, 0x07ff, 0x07e0, 0xf81f, 0xf800, 0x001f, 0
    };
    volatile uint16_t *pixels;
    unsigned short x, y, height;
    if (!me_video_enter(&state, 0))
        return 0;
    pixels = (volatile uint16_t *)A2560ME_VIDEO_BASE;
    height = me_height(0);
    for (y = 0; y < height; y++)
        for (x = 0; x < 1280; x++)
            *pixels++ = colours[x / 160];
    return 1;
}
static long restore(void)
{
    me_video_leave(&state);
    return 0;
}
static long cookie(const char *name)
{
    const uint32_t *jar = *(const uint32_t * volatile *)0x5a0;
    uint32_t key = ((uint32_t)name[0] << 24) | ((uint32_t)name[1] << 16) |
        ((uint32_t)name[2] << 8) | (uint32_t)name[3];
    while (jar && jar[0])
    {
        if (jar[0] == key)
            return jar[1];
        jar += 2;
    }
    return -1;
}
static long compatible(void)
{
    return cookie("_MCH") == 0xf258 && cookie("_CPU") == 60 &&
        cookie("FVRM") == A2560ME_VIDEO_BASE && cookie("fVDI") == -1;
}
long probe_main(void);
long probe_main(void)
{
    (void)Cconws("RGB565 test: run from the recovery shell, before loading fVDI.\r\n");
    if (!Supexec(compatible))
    {
        (void)Cconws("Compatible A2560Me DDR/video-reservation firmware required.\r\n");
        return 1;
    }
    (void)Cconws("Eight bars: white yellow cyan green magenta red blue black.\r\nPress any key to restore monochrome.\r\n");
    if (!Supexec(pattern))
    {
        (void)Cconws("Refused: DDR endian inversion or GGE is active.\r\n");
        return 1;
    }
    (void)Cnecin();
    (void)Supexec(restore);
    (void)Cconws("Monochrome display restored.\r\n");
    return 0;
}
