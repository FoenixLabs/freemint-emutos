# gemtos-a2560me

Fork of EmuTOS 1.4 for Foenix Retro Systems m68k machines. Active target is the **A2560Me** (Makefile/define still use `a2560m` / `MACHINE_A2560M`). Hobby project; GPL-2.0-or-later.

Upstream EmuTOS docs live in `doc/`. Foenix port notes: `readme.md`, `doc/genxtos.md`. Coding rules: `doc/coding.txt` and `doc/old_code.txt`.

## Hardware (A2560Me)

- CPU: 68EC060 @ 50 MHz. Build with `-m68060 -mshort -msoft-float`. There is no FPU; omitting `-msoft-float` makes interrupt handlers save FPU registers and crash.
- SRAM: 8 MB (`SRAM_TOP` `0x00800000`). TOS-style 1bpp video RAM sits in SRAM at `0x00700000` (1 MB).
- Chipset: GAVIN `0xFEC00000`, SuperIO `0xFEC02000`, VICKY2 (legacy text) `0xFEC80000`, VICKY3 (DDR3 bitmap) `0xFC000000`.
- I/O: PS/2 keyboard/mouse, RTC (BQ4802LY), UART 16550 (debug on COM3), SD/MMC. IDE is off on this target.
- Storage: Atari-partitioned media, FAT12/FAT16 only. Prepare images with Hatari.

`CPUFLAGS = -m68060` for A2560M/K/X. A2560U is 68000 @ 20 MHz and a different memory map (`foenix/foenix.h`).

## Build

Toolchain: Vincent Rivière `m68k-atari-mint-gcc` (GCC 4.6–4.8). GNU make required.

```sh
./compile.sh
# equivalent:
( cd foenix && make -j4 )
make UNIQUE=us a2560m -j4
```

Outputs: `emutos.img`, `emutos-a2560m.rom` (512 KB padded), `emutos.map`.

- `UNIQUE=xx` is a single-country build (language + keyboard). `COUNTRY=xx` keeps all countries.
- `make clean` before switching targets. Same-target language change is the only exception.
- `localconf.h` overrides `include/config.h` (gitignored). Do `make clean` after changing either.
- Foenix HAL is `foenix/libfoenix-a2560m.a`, built by the top-level Makefile via `foenix/Makefile`.

Other Foenix targets: `a2560u`, `a2560x`, `a2560k`, `c256genx`. AES is **disabled** on A2560M (`WITH_AES 0` in `include/config.h`).

## Deploy

Link address is `ROM_ORIGIN` in `emutos.ld`. Rebuild after changing it.

| Mode | `ROM_ORIGIN` | Upload |
|------|----------------|--------|
| RAM (dev, current default) | `0x00100000` | `./upload-to-mem.sh` |
| Flash (A2560M/X/K/GenX) | `0xffc00000` (FLASH0) | `./upload-to-flash.sh` |
| Flash (A2560U) | `0x00f00000` | `./upload-to-flash.sh` |

Scripts use FoenixMgr as `fm.sh --port /dev/ttyUSB1`. RAM load also uploads `tools/ldemutos.s28` so the reset vector points at `0x100000`.

## Layout

| Path | Role |
|------|------|
| `bios/` | TOS BIOS/XBIOS, startup, screen, keyboard, disk, Foenix glue (`a2560_bios*.c`, `a2560_conout_*`, `screen_vicky2.c`, `screen_vicky3.c`, `screen_1bpp.c`) |
| `bdos/` | GEMDOS filesystem, processes, memory |
| `vdi/` | VDI / Line-A |
| `aes/` | AES (not in A2560M image) |
| `desk/` | EmuDesk |
| `cli/` | EmuCON |
| `foenix/` | Standalone HAL: GAVIN, VICKY, PS/2, UART, timers, interrupts, shadow FB |
| `include/` | Shared headers. Every EmuTOS C file starts with `#include "emutos.h"` |
| `util/` | Shared helpers |
| `tools/` | Host tools (`mkrom`, `localise`, …) |
| `po/` | Translations |
| `linker/`, `emutos.ld`, `tosvars.ld` | Memory map |

Foenix code is gated with `MACHINE_A2560M` / `MACHINE_FOENIX` (the latter is defined for all A2560/GenX machines).

## Config

- Defaults: `include/config.h`. New options must be `#ifndef`-guarded so `localconf.h` can override.
- Non-overridable system defines: `include/sysconf.h`.
- A2560M block (~line 840 of `config.h`): no Atari hardware, SD on / IDE off, EmuCON on, AES off, debug via `FOENIX_COM3_DEBUG_PRINT`.
- At least one of `CONF_WITH_A2560_TEXT_MODE` and `CONF_WITH_A2560_SHADOW_FRAMEBUFFER` is required for a usable console; both are currently 0 on A2560M (1bpp TOS graph / VICKY3 path instead).
- `CONF_ATARI_HARDWARE` is 0. Do not re-enable Atari-only drivers (MFP, IKBD ACIA, shifter, ACSI, …) on this target.

## Coding

Follow `doc/coding.txt`. Match the file you edit.

- Unix LF, no hard tabs in `.c`/`.h`/`.S`, no trailing spaces. Indent 4 spaces.
- `make gitready` expands tabs and normalizes EOL.
- Compile clean under `WARNFLAGS` (`-Wall` plus several `-Werror=`). Do not add `-Werror` globally.
- EmuTOS C: `#include "emutos.h"` first. Types from `portab.h`: `UBYTE`/`UWORD`/`ULONG`/`WORD`/`LONG`/`BOOL`. **`int`/`WORD` are 16-bit** (`-mshort`). Pointers and `LONG` are 32-bit.
- Foenix HAL may use `stdint.h` / `stdbool.h` / C99 (`foenix/Makefile` uses `-std=c99`).
- Hardware: `R8`/`R16`/`R32`/`GAVIN_R` from `foenix/regutils.h`. Size must match the bus. On A2560M, GAVIN is 32-bit (`GAVIN_R` = `R32`).
- `.data` lives in ROM and is read-only. Initialized globals must be `const` (they go in `.text`). Mutable state is BSS or explicit RAM.
- Assembler symbols visible from C: leading `_`, CDECL (args on stack, d0-d1/a0-a1 scratch, return in d0). See `doc/coding.txt`.
- Keep preprocessor conditionals brace-balanced (`doc/coding.txt`).
- Do not assume `char` is signed. Do not use `0xffffffff` as `-1`. See `doc/old_code.txt`.
- New files: same GPL header as neighbors (copyright, author initials, `doc/license.txt`).
- Do not reformat whole files. Do not add AES to the A2560M image unless that is the task.

## Foenix pitfalls

- VICKY bitmap VRAM is generally **write-only**. Text scroll/invert/readback needs the shadow framebuffer (`foenix/shadow_fb.c`) or VICKY text mode. A2560Me TOS graph uses SRAM, which is CPU-readable.
- Console drivers: `a2560_conout_text.c` (VICKY text), `a2560_conout_bmp.c` / `_1bpp.c` (shadow/TOS graph). Chosen in `a2560_bios_get_conout()`.
- Line-A belongs to the BIOS in this port. Mouse: VICKY hardware cursor plus a synthetic IKBD packet so AES/VDI see motion (`foenix/ps2_mouse_a2560.c`).
- Keyboard is **PS/2 scancodes** (Linux-style, `foenix/ps2_scancodes.h`), not Atari IKBD. Layout tables: `bios/keyb_*.h`.
- Do not use `STOP` (`USE_STOP_INSN_TO_FREE_HOST_CPU` is forced off; it crashes).
- Empty delay loops need `DONT_OPTIMIZE_OUT` (`foenix/regutils.h`).
- VDI graphics are not done: Atari VDI expects a readable shifter framebuffer.

## Debug

- `KDEBUG(("fmt", args))` after `#define ENABLE_KDEBUG` in that file (`include/kprint.h`). Extra parens are required.
- Foenix: `a2560_debugnl()` / `a2560_debug()` (`foenix/a2560_debug.h`). On A2560M this goes to COM3 (`FOENIX_COM3_DEBUG_PRINT`).
- `emutos.map` for link addresses; `make dsm` for a disassembly dump.

## Tests

`tests/` is Hatari/ARAnyM-oriented, not a Foenix board test suite. After BIOS/screen/keyboard/disk changes, rebuild `a2560m` and load to RAM with `./upload-to-mem.sh`.
