A2560Me EmuTOS + FreeMiNT + accelerated fVDI desktop
=================================================
Release: 2026-10-17, experimental board port

Contents
- emutos-a2560m.rom: 512 KiB DDR-aware FLASH image, base 0xFFD00000,
  reset PC 0xFFD00008. This is the normal image to flash.
- emutos-a2560m-sram.rom: same flash address, DDR disabled for recovery.
- emutos-a2560m-ram.rom: development image linked at 0x00100000; DO NOT FLASH.
- drive_c/: boot kernel/configuration for FAT16 C:.
- drive_d/: FAT32 D: installation, colour startup, AES, desktop, diagnostics,
  component sources, patches, licenses and offline rebuild scripts.
- source/EMUTOSSRC.TGZ: complete EmuTOS working-source snapshot including
  the board/HAL changes, fVDI driver, build helpers and release profile.
- tools/a2560me_dbg.py: vendor debug-protocol v2 host tool.
- upload-to-flash.sh: default vendor flash command; PORT overrides ttyUSB1.
- VALIDATION.TXT, BUILD.TXT and SHA256.TXT: results, provenance, checksums.

Install
1. Back up existing partitions, files and desktop settings. Use an existing
   compatible FAT16 C: and FAT32 D: layout; this package does not partition
   or format disks. Other hardware/CPU targets are not supported by this ROM.
2. Copy CONTENTS of drive_c/ to C: and drive_d/ to D:, merging folders.
   Preserve existing TERADESK.INF and other user files; do not use a mirror
   operation that deletes files missing from this package.
3. Install Python 3 and pyserial on the flashing host (for example, install
   pyserial in a virtual environment). Connect the vendor debug interface.
   From the extracted package on Linux:
       ./upload-to-flash.sh
   Equivalent:
       python3 tools/a2560me_dbg.py --port /dev/ttyUSB1 --flash emutos-a2560m.rom --block 2 --layout 512k
   Confirm the correct debug port. The tool erases/programs only this
   512 KiB image, verifies it and resets the target.
4. Expect EmuTOS -> FreeMiNT -> fVDI -> XaAES -> TeraDesk in RGB565 colour.
   Default 1280x960, or 1280x1024 when that timing is already selected.
   The current setup uses 1280x960 and was tested at that timing.
5. Read D:/GUI.TXT and D:/MINT/FVDI/README.TXT for tests and recovery.

Memory and graphics
8 MiB SRAM plus DDR; 1008 MiB alternate RAM, with top 8 MiB reserved for
video. FastTotal reports usable DDR, CoreTotal usable SRAM, MemTotal their
sum. Totals exclude boot allocations. Driver uses write-through CPU cache
and synchronous VDMA for large copies/solid fills. Other drawing uses CPU
fallbacks. No FPU, MMU protection, MDMA or SDMA support is required/enabled.
Video Options lists valid Foenix modes; it does not switch modes live.
For half width, add 'half' to the a2560me.sys line in D:/MINT/FVDI/FVDI.SYS
before booting. Actual half-mode switching has not been target-validated.

Recovery
Copy D:/MINT/MONO.CNF over D:/MINT/MINT.CNF and reboot for monochrome;
SHELL.CNF instead selects internal shell. Rename C:/AUTO/MINT060.PRG to
MINT060.PRX to skip FreeMiNT. If DDR firmware will not boot, flash the
SRAM recovery image:
    ./upload-to-flash.sh emutos-a2560m-sram.rom
Use MONO.CNF with SRAM-only firmware. Restore the main ROM and colour
MINT.CNF from FVDI.CNF to return to the accelerated setup.

Rebuild
Unpack source/EMUTOSSRC.TGZ into a working directory. It creates emutos/.
Unpack drive_d/MINT/SOURCE/LIBSRC.TGZ beside emutos/ to create mintlib/.
Install Vincent Riviere m68k-atari-mint GCC/binutils (tested GCC 4.6.4),
GNU make and native GCC, then run ./compile.sh inside emutos/. This uses
the recorded firmware-localconf.h profile and produces flash, RAM and SRAM
recovery ROMs. Existing differing localconf.h is preserved and rejected
until reviewed. Build logs go to logs/fvdi/. No FPGA or ROM source is
silently fetched by this firmware build; MiNTLib sources are supplied.
For the components on C:/D:, use BUILD.SH, GUIBUILD.SH, FVBUILD.SH and
TDBUILD.SH with their source archives/patches under D:/MINT/SOURCE.
See that folder's README.TXT, GUI.TXT and FVDI.TXT for dependencies/recipes.
Build timestamps can change hashes; source snapshot records this release.

Licenses
EmuTOS and new board glue: GPL-2.0-or-later, see COPYING and EmuTOS
source doc/license.txt. FreeMiNT, MiNTLib, GEMLib, fVDI and TeraDesk retain
their own notices/licenses in the supplied complete component sources.
Generic rendering files retain upstream public-domain/GPL notices.
The vendor debug tool is supplied as received, separately from the board
port's licensing notice. Upstream original TeraDesk archive is retained
for provenance; the shipped executable is rebuilt with TERAVID.PAT.
