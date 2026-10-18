A2560Me - EmuTOS, FreeMiNT, fVDI, XaAES and TeraDesk
==================================================

This package boots a 1280x960 RGB565 desktop with CPU caching and VDMA
acceleration. It targets the A2560Me 68LC/EC060 board with no FPU.

Installation
1. Back up both partitions and user settings. Copy the CONTENTS of drive_c
   to FAT16 C: and drive_d to FAT32 D:, merging folders. Do not format by
   copying. Preserve your DESKTOP/TERADESK.INF; it is not supplied here.
2. Flash the supplied emutos-a2560m.rom using the vendor debug tool:
   python3 tools/a2560me_dbg.py --port /dev/ttyUSB1 --flash emutos-a2560m.rom --block 2 --layout 512k
   The image is 512 KiB at 0xFFD00000; reset PC is 0xFFD00008. This DDR-aware
   firmware is REQUIRED for colour; the prior SRAM-only firmware is not enough.
3. Reboot. Expect EmuTOS -> FreeMiNT -> fVDI -> XaAES -> TeraDesk in colour.
   D:/MINT/MINT.CNF selects colour startup; C: includes that configuration.
   Disable unrelated AUTO programs/accessories for the first boot.

Memory: 8 MiB physical SRAM plus DDR. 1008 MiB DDR is registered as alternate
RAM; top 8 MiB is reserved for video and never allocated to applications.
CoreTotal is usable SRAM; FastTotal is usable alternate RAM; MemTotal adds
both. Boot allocations reduce the reported totals.

Kernel: 68060 soft-float, no FPU probing, no STOP/LPSTOP, MMU support off.
C: uses EmuTOS GEMDOS, D: uses FreeMiNT FAT32. The BIOS provides keyboard
vector and _5MS timer hooks needed by FreeMiNT.

Recovery
Copy D:/MINT/MONO.CNF over D:/MINT/MINT.CNF for monochrome, or SHELL.CNF for
internal shell, then reboot. Rename C:/AUTO/MINT060.PRG to MINT060.PRX to
skip MiNT. If DDR firmware fails, flash the supplied emutos-a2560m-sram.rom
with the same command and use MONO.CNF. The RAM ROM is a development image;
do not flash it. Never substitute a ROM linked at a different address.

Physical validation passed: flash programming/readback and colour boot;
DDR pattern, cache/VDMA copy/fill/readback/overlap; physical mouse, window
dragging and redraw. Video Options reports valid modes. Longer stress and
half-resolution switching are not validated. This is an experimental board
port, not an official upstream release.

Read D:/GUI.TXT and D:/MINT/FVDI/README.TXT. Matching component sources,
patches, licenses and build recipes are in D:/MINT/SOURCE. Full EmuTOS
working-source snapshot is included in the release's source/ folder.
SHA256.TXT covers supplied files only; user settings are not included.
