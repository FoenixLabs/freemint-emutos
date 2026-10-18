/*
 * A2560Me DDR3 allocation map (hardware reference rev 1.8).
 * Copyright (C) 2026 The EmuTOS development team
 * GPL version 2 or later; see doc/license.txt.
 */
#ifndef A2560ME_MEMORY_H
#define A2560ME_MEMORY_H

/* The low 8 MiB of DDR3 are hidden behind SRAM in the CPU address map. */
#define A2560ME_DDR_BASE       0x00800000UL
#define A2560ME_DDR_TOP        0x40000000UL
/* Keep 8 MiB for a 1280x1024 32-bpp surface plus cursor/scratch space. */
#define A2560ME_VIDEO_BASE     0x3f800000UL
#define A2560ME_VIDEO_SIZE     (A2560ME_DDR_TOP - A2560ME_VIDEO_BASE)
#define A2560ME_ALT_SIZE       (A2560ME_VIDEO_BASE - A2560ME_DDR_BASE)
/* FVRM advertises the excluded framebuffer region to the fVDI driver. */
#define A2560ME_VIDEO_COOKIE   0x4656524dUL

#endif
