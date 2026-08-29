/*
 * VICKY2 - Functions for VICKY II, the graphics controller of the Foenix
 *
 * Copyright (C) 2021-2025 The EmuTOS development team
 *
 * Authors:
 *  VB   Vincent Barrilliot
 *
 * This file is distributed under the GPL, version 2 or at your
 * option any later version.  See doc/license.txt for details.
 */

#ifndef VICKY2_H
#define VICKY2_H

#include <stdint.h>
#include "foenix.h"


/* VICKY II */
/*#define VICKY_CTRL                  VICKY*/
    #define VICKY_CTRL_TEXT       0x00000001        /* Block Text and MemText Enable*/
    #define VICKY_CTRL_TXTOVERLAY 0x00000002
    #define VICKY_CTRL_GFX        0x00000004        /* VICKY III/IV Graphic Engine Enable - Not the GEMTOS Bitmap */
    /* Beware VICKY II mode of the A2560M doesn't have bitmap */
    #define VICKY_CTRL_BITMAP     0x00000008        /* Enable the Bitmap in GUI or GAME Mode - Not the GEMTOS Bitmap */
    #define VICKY_CTRL_TILE       0x00000010        /* Enable the TileMap in GAME Mode */
    #define VICKY_CTRL_SPRITE     0x00000020        /* Enable the Sprite in GAME Mode */
    #define VICKY_GAMMA_ENABLE    0x00000040        /* Either Set Manually, or Read the Value from DIPSwitch - By Default, the DipSwitch choses the value see VICKY_Reg[17] to switch it to software programmable */
    #define VICKY_CTRL_DISABLE    0x00000080        /* Not Used Presently */
    #define VICKY_VIDEO_MODE0     0x00000100        /* VideoMode[0] : 2'b00: 1280x960, 2'b01: 1280x1024, 2'b10: 1280x720^^, 2'b11: 1920x1080^^ - ^^: Not implemented yet */
    #define VICKY_VIDEO_MODE1     0x00000200        /* VideoMode[1] */
    #define VICKY_PIXEL_DIV0      0x00000400        /* Pixel Division[0] for Game Mode: 2'b00: 1:1, 2'b01: 2:1, 2'b10: 4:1, 2'b11: 1:1 */
    #define VICKY_PIXEL_DIV1      0x00000800        /* Pixel Division[1] for Game Mode */
    #define VICKY_TURN_SYNC_OFF   0x00001000        /* By Setting to 1, you put the monitor in Sleep Mode */
    #define VICKY_FONT_OVR_BG     0x00002000        /* When in overlay mode (block Text mode), the $00 Color in the LUT shows what is behind (i.e. Bitmap, etc...)*/
    #define VICKY_MEMTEXT_ENABLE  0x00004000        /* Turn the Memtext Mode on - (Mutually exclusive with the GEMTOS Bitmap) */
    #define VICKY_MEMTEXT_OVR_BG  0x00008000        /* Same has "VICKY_FONT_OVR_BG" but for the memtext system */
    #define VICKY_GUI_GAME_MODE   0x00010000        /* Set the Graphic Engine in GUI or GAME Mode */
    #define VICKY_GAMMA_SRC_SLCT  0x00020000        /* When 0, the GAMMA is set by DIPSWitch Input, When 1, the value of "VICKY_GAMMA_ENABLE" applies */
    #define VICKY_18_UNDEFINED    0x00040000
    #define VICKY_19_UNDEFINED    0x00080000
    #define VICKY_TOS_BITMAP_EN   0x00100000        /* Already defined in the foenix.h, but I thought, it would be good to document it here*/
    #define VICKY_21_UNDEFINED    0x00200000        /* These 2 bit [22:21] are not used, the Color mode for the TOSBitmap are set in the TOS Bitmap register Level */
    #define VICKY_22_UNDEFINED    0x00400000        /* These 2 bit [22:21] are not used, the Color mode for the TOSBitmap are set in the TOS Bitmap register Level */
    #define VICKY_23_UNDEFINED    0x00800000
    #define VICKY_LAYER0_ON       0x01000000        /* Enable the Layer 0 in the GAME MODE */
    #define VICKY_LAYER0_TYPE     0x02000000        /* Define the Layer 0 for Bitmap or Tile */
    #define VICKY_LAYER1_ON       0x04000000        /* Enable the Layer 1 in the GAME MODE */
    #define VICKY_LAYER1_TYPE     0x08000000        /* Define the Layer 1 for Bitmap or Tile */
    #define VICKY_LAYER2_ON       0x10000000        /* Enable the Layer 2 in the GAME MODE */
    #define VICKY_LAYER2_TYPE     0x20000000        /* Define the Layer 2 for Bitmap or Tile (Write Only)*/
    #define VICKY_LAYER3_ON       0x40000000        /* Enable the Layer 3 in the GAME MODE (Write Only) */
    #define VICKY_LAYER3_TYPE     0x80000000        /* Define the Layer 3 for Bitmap or Tile (Write Only)*/
/* This is pretty much Deprecated in the A2560Me */
    #define VICKY_CTRL_HIGH_RES   0x40000000  /* See MCP txt_a2560k_b.c */
    #define VICKY_CTRL_CLK40      0x80000000  /**< Indicate if PLL is 25MHz (0) or 40MHz (1) */

    #define VICKY_BORDER_HEIGHT   0x003f0000L
/* Channel A (first screen), VICKY II has only one anyway */
/*#define VICKY_A_BORDER_CTRL         (VICKY+0x0004) */ /* Border control */
    #define VICKY_BORDER_ENABLE   0x00000001
    #define VICKY_BORDER_SCROLLX  0x00000070
    #define VICKY_BORDER_WIDTH    0x00003f00L
    #define VICKY_BORDER_HEIGHT   0x003f0000L

/*#define VICKY_B_BORDER_COLOR        (VICKY+0x0008) */ /* Border colour 0x--RRGGBB */
/*#define VICKY_A_CURSOR_CTRL         (VICKY+0x0010) */ /* Cursor configuration */
    #define VICKY_CURSOR_ENABLE     0x00000001
    #define VICKY_CURSOR_RATE       0x00000006
    #define VICKY_CURSOR_CHAR       0x00ff0000L

/*#define VICKY_A_CURSOR_POS          (VICKY+0x0014) */ /* Cursor position */
    #define VICKY_CURSOR_X          0x0000ffff
    #define VICKY_CURSOR_Y          0xffff0000
#define VICKY_B_BG_COLOR            (VICKY+0x000C)  /* Background control */
/*#define VICKY_A_BMP0_FG_CTRL        (VICKY+0x0100) */ /* Bitmap layer 0 control */
/*#define VICKY_A_BMP0_FB             (VICKY+0x0104) */ /* Bitmap layer 0 framebuffer address relative to VRAM */
/*#define VICKY_A_BMP1_FG_CTRL        (VICKY+0x0108) */ /* Bitmap layer 1 control */
/*#define VICKY_A_BMP1_FB             (VICKY+0x010c) */ /* Bitmap layer 1 framebuffer address relative to VRAM */

/* Color palettes */
#define VICKY_NLUTS           8      /* Number of luts */

/* Mouse */
#define VICKY_MOUSE_MEM         (VICKY+VICKY_MOUSE_MEM_OFFSET)
#define VICKY_MOUSE_CTRL        (VICKY+VICKY_MOUSE_CTRL_OFFSET)
    #define VICKY_MOUSE_ENABLE  1
    #define VICKY_MOUSE_CHOICE  2
#define VICKY_MOUSE_SUPPORT   (VICKY+0x0C02)
#define VICKY_MOUSE_X         (VICKY_MOUSE_SUPPORT)
#define VICKY_MOUSE_Y         (VICKY_MOUSE_SUPPORT+2)
#define VICKY_MOUSE_PACKET    (VICKY_MOUSE_SUPPORT+8) /* 3 words (16bits)/ PS/2 mouse packet that VICKY knows how to interpret */

/* Text memory */
#define VICKY_TEXT_COLOR      (VICKY_FONT) /* Font memory (-> 0xbfff) */
#define VICKY_TEXT_COLOR_FG   (VICKY_TEXT+0xC400) /* Text foreground colours 16x 32bit colors (-> 0x43f) */
#define VICKY_TEXT_COLOR_BG   (VICKY_TEXT+0xC440) /* Text foreground colours 16x 32bit colors (-> 0x47f) */


/* Normal pixels */
#ifdef MACHINE_A2560U
#define VICKY_MODE_MASK       0x00000700L
#define VICKY_MODE_640x480_60 0x00
#define VICKY_MODE_800x600_60 0x01
#define VICKY_MODE_RESERVED2  0x02
#define VICKY_MODE_640x400_70 0x03
/* Doubled pixels */
#define VICKY_MODE_320x240_60 0x04
#define VICKY_MODE_400x300_60 0x05
#define VICKY_MODE_RESERVED6  0x06
#define VICKY_MODE_320x200_70 0x07

#define VICKY_TEXT_COLOR_SIZE 32  /* 16 colors of 2 words each */

#elif defined(MACHINE_A2560K) || defined(MACHINE_A2560X) || defined(MACHINE_GENX)
#define VICKY_MODE_MASK       0x00000700L
/* Channel A (text only) */
#define VICKY_A_MODE_800x600_60  0x00
#define VICKY_A_MODE_1024x768_60 0x01
/* Channel B (full featured) */
#define VICKY_B_MODE_640x480_60  0x00
#define VICKY_B_MODE_800x600_60  0x01
#define VICKY_B_MODE_RESERVED2   0x02
#define VICKY_B_MODE_640x400_70  0x03
/* Doubled pixels mode */
#define VICKY_B_MODE_320x240_60  0x04
#define VICKY_B_MODE_400x300_60  0x05
#define VICKY_B_MODE_RESERVED6   0x06
#define VICKY_B_MODE_320x200_70  0x07

#define VICKY_TEXT_COLOR_SIZE 16  /* 16 colors of 1 (32bit) words each */

#elif defined(MACHINE_A2560M)
#define VICKY_MODE_MASK       0x0000000EL
#define VICKY_TEXT_COLOR_SIZE 16  /* 16 colors of 1 (32bit) words each */
#endif


typedef struct {
    uint16_t id;
    uint16_t w;
    uint16_t h;
    uint16_t bpp; /* Bits per plane */
    uint8_t  fps;
} FOENIX_VIDEO_MODE;


extern const uint16_t vicky2_default_palette[];

#ifdef MACHINE_A2560U
union vicky2_color_t {
    uint32_t code;
    struct __attribute__((__packed__)) {
        uint8_t blue;
        uint8_t green;
        uint8_t red; 
        uint8_t alpha;
    };
};
#elif defined(MACHINE_A2560K) || defined(MACHINE_A2560M) || defined(MACHINE_A2560X) || defined(MACHINE_GENX)
union vicky2_color_t {
    uint32_t code;
    struct __attribute__((__packed__)) {
        uint8_t alpha;
        uint8_t red;
        uint8_t green;
        uint8_t blue;
    };
};
#endif
typedef union vicky2_color_t COLOR32;

struct vicky2_text_memory_t {
    uint8_t text[VICKY_TEXT_SIZE];
    uint8_t reserved_4000[0x4000];
    uint8_t color[VICKY_TEXT_SIZE];
    uint8_t reserved_c000[0x400];
    union vicky2_color_t palette_fg[16];
    union vicky2_color_t palette_bg[16];
};

struct vicky2_layer_t {
    uint32_t control;
    uint8_t  *address; /* Relative to VRAM start */
};

struct vicky2_bitmap_t {
    struct vicky2_layer_t layer[3]; /* Bitmap 0, bitmap 1, collision detection */
};

struct vicky2_palette_t {
    union vicky2_color_t color[256];
};

struct vicky2_bmp_palette_t {
    struct vicky2_palette_t lut[VICKY_NLUTS];
};

struct vicky2_font_memory_t {
    uint8_t mem[VICKY_FONT_SIZE];
};

#ifdef MACHINE_A2560U
/* A2560 */
struct vicky2_t {
    uint32_t control;
    uint32_t border_control;
    uint32_t border_color;
    uint32_t background_color;
    uint32_t cursor_control;
    uint32_t cursor_position;
    uint16_t line_interrupt[4];
    uint16_t reserved[8];
    uint16_t fpga_year;
    uint16_t fpga_month_day;
    uint16_t pcb_revision[2]; /* Null-terminated string */
    uint16_t fpga_sub_version;
    uint16_t fpga_version;
    uint16_t fpga_part_number_low;
    uint16_t fpga_part_number_high;
};

struct vicky2_channel_t {
    struct vicky2_t *ctrl;
    struct vicky2_bitmap_t *bitmap;
    struct vicky2_tile_t *tile;
    struct vicky2_collision_t *collision;
    struct vicky2_mouse_gfx_t *mouse_gfx;
    struct vicky2_mouse_control_t *mouse_control;
    struct vicky2_sprites_control_t **sprite;
    struct vicky2_bmp_palette_t *lut;
    struct vicky2_gamma_lut_memory_t *gamma;
    struct vicky2_font_memory_t *font_memory;
    struct vicky2_text_memory_t *text_memory;
    const FOENIX_VIDEO_MODE *video_modes; // Array of video modes
};

extern const struct vicky2_channel_t * const vicky;

#elif defined(MACHINE_A2560K) || defined(MACHINE_A2560M) || defined(MACHINE_A2560X) || defined(MACHINE_GENX)
struct vicky2_mouse_control_t {
    uint16_t control; /* READ AS 32BITS ! */
    uint16_t reserved02;
    uint16_t yx; /* Read only */
    uint16_t reserved06;
};

struct vicky2_t {
    uint32_t control;
#if defined(MACHINE_A2560M)
    uint8_t *bitmap_address;
    COLOR32  mono_color;
    uint32_t unused_0c;
#else
    uint32_t border_control;
    uint32_t border_color;
    uint32_t background_color;
#endif
    uint32_t cursor_control;
    uint32_t cursor_position;
    uint32_t line_interrupt_01;
    uint32_t line_interrupt_23;
    uint32_t font_size_control;
#if defined(MACHINE_A2560M)
    uint32_t text_window_size;
    uint32_t window_pos_x;
    uint32_t window_size_x;
    uint32_t window_prefetch;
    uint32_t reserved_0028[3];
#else
    uint32_t font_count_control;
    uint32_t reserved_0028[6];
#endif
    
    uint32_t mouse_graphics[16*16*2];
    uint16_t mouse_control; /* Must write as 32bits ! */
    uint16_t reserved_c02;
    uint32_t mouse_position; /* Read only */
    uint16_t reserved_c06;
    uint32_t ps2_byte[3]; /* Must write as 32 bits. See doc. */
};

struct vicky2_mouse_gfx_t {
    uint32_t mouse_gfx[8];
};

struct vicky2_sprite_control_t {
    uint16_t control;
    uint16_t address; /* Must be on 16bit boundary address */
};

struct vicky2_sprites_control_t {
    struct vicky2_sprite_control_t sprite[64];
};

struct __attribute__((__packed__)) vicky2_gamma_lut_memory_t {
    uint8_t blue[256];
    uint8_t green[256];
    uint8_t red[256];
};

struct vicky2_channel_t {
    struct vicky2_t *ctrl;
    struct vicky2_bitmap_t *bitmap;
    struct vicky2_tile_t *tile;
    struct vicky2_collision_t *collision;
    struct vicky2_mouse_gfx_t *mouse_gfx;
    struct vicky2_mouse_control_t *mouse_control;
    struct vicky2_sprites_control_t **sprite;
    struct vicky2_bmp_palette_t *lut;
    struct vicky2_gamma_lut_memory_t *gamma;
    struct vicky2_font_memory_t *font_memory;
    struct vicky2_text_memory_t *text_memory;
    const FOENIX_VIDEO_MODE *video_modes; /* Array of video modes */
};

/* Convenience pointers for the default (or only) screen */
extern const struct vicky2_channel_t vicky2_channel_a;
extern const struct vicky2_channel_t vicky2_channel_b;
/* Convenience, will point to either vicky2_channel_a or vicky2_channel_b depending on the machine. */
extern const struct vicky2_channel_t * const vicky;

#endif

extern uint32_t vicky_vbl_freq; /* VBL frequency */

void vicky2_init(void);
void vicky2_init_channel(const struct vicky2_channel_t * const vicky);

#if !defined(MACHINE_A2560M)
/* Color management */
void vicky2_set_background_color(const struct vicky2_channel_t * const vicky, uint32_t color);
void vicky2_set_border_color(const struct vicky2_channel_t * const vicky, uint32_t color);
#endif

void vicky2_set_lut_color(const struct vicky2_channel_t * const vicky, uint16_t lut, uint16_t number, uint32_t color);
void vicky2_get_lut_color(const struct vicky2_channel_t * const vicky, uint16_t lut, uint16_t number, COLOR32 *result);

/* Video mode */
void vicky2_set_video_mode(const struct vicky2_channel_t * const vicky, uint16_t mode); /* video mode number */
void vicky2_read_video_mode(const struct vicky2_channel_t * const vicky, FOENIX_VIDEO_MODE *result);
void vicky2_set_bitmap_address(const struct vicky2_channel_t * const vicky, uint16_t layer, const uint8_t *address); /* address is relative to VRAM */
uint8_t *vicky2_get_bitmap_address(const struct vicky2_channel_t * const vicky, uint16_t layer); /* address is relative to VRAM */

/* Text output support */
void vicky2_set_text_lut(const struct vicky2_channel_t * const vicky, const uint16_t *fg, const uint16_t *bg);

/* Text cursor support */
void vicky2_show_cursor(const struct vicky2_channel_t * const vicky);
void vicky2_hide_cursor(const struct vicky2_channel_t * const vicky);
void vicky2_set_text_cursor_xy(const struct vicky2_channel_t * const vicky, uint16_t x, uint16_t y);

/* Mouse support: see vicky_mouse.h */

/* Utility */
uint32_t convert_atari2vicky_color(uint16_t orgb);

#endif /* VICKY2_H */
