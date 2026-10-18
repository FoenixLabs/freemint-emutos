A2560Me fVDI + DDR3 test procedure
================================

This package adds an RGB565 driver for the GUI bitmap engine in DDR3.
MINT.CNF now enables the colour desktop. MONO.CNF preserves the validated
monochrome startup; SHELL.CNF preserves internal-shell recovery. The prior
colour driver passed DDR/scanout/GUI tests; this revision adds cache/VDMA.

1. Firmware and files
---------------------
The new EmuTOS firmware must register the DDR memory map and FVRM cookie.
On the Linux host, the normal ./upload-to-flash.sh flashes the rebuilt
emutos-a2560m.rom at 0xFFD00000. emutos-a2560m-sram.rom is the recovery
variant with DDR registration disabled. The main ROM was flashed, read
back byte-for-byte, and booted into the colour desktop on 2026-10-17.

Copy the updated drive_d/ contents to D:, merging folders. In particular,
copy MINT/FVDI/, MINT/FVDI.CNF and MINT/MONO.CNF. Keep your existing
DESKTOP/TERADESK.INF and all user files. The supplied MINT/MINT.CNF is
now the colour GUI configuration.

With DDR-aware firmware, U:/KERN/MEMINFO should show alternate memory in
FastTotal (nominally about 1,032,192 kB before allocations/rounding).
A physical RAM boot on 2026-10-17 reported FastTotal 1,031,632 kB
after boot allocations. CoreTotal was 5,888 kB and MemTotal 1,037,520 kB.
The temporary RAM firmware consumes SRAM; the flash build frees that space.
CoreTotal remains the usable SRAM pool. The top 8 MiB of DDR3 are reserved
for video and must never appear in FastTotal or Mxalloc allocations.

2. Validate DDR and scanout from the recovery shell
-------------------------------------------------
Copy D:/MINT/SHELL.CNF over D:/MINT/MINT.CNF and reboot. From the shell:
    /d/mint/fvdi/ramtest.tos
Expect PASS after an alternate-RAM allocation and a 4 MiB pattern test.
This samples memory; it is not a complete 1 GiB memory stress test.

Then run:
    /d/mint/fvdi/guipat.tos
Expect eight vertical bars: white, yellow, cyan, green, magenta, red,
blue, black. Press any key to restore the monochrome console. The program
refuses old firmware or an already installed fVDI. If the display is wrong,
record a photo and do not proceed to the desktop test.

3. Validate the cache/VDMA desktop
-------------------------
On the host, copy D:/MINT/FVDI.CNF over D:/MINT/MINT.CNF, then reboot.
It changes directory to D:/MINT/FVDI before starting FVDI.PRG so the engine
finds FVDI.SYS. XaAES and TeraDesk start afterwards, using the same files
as the working monochrome installation.

Default bitmap mode is 1280x960 RGB565 (65,536 colours), or 1280x1024 if
that timing is already selected. No timing change is performed. An optional
'half' token on the driver line in FVDI.SYS selects 640x480/512 RGB565.
The initial driver does not implement indexed 8-bit or 32-bit modes.

Check menus, fonts, colours, cursor shapes, clicks, scrolling, typing,
window dragging, overlapping-window redraw and saved settings. Check for
stale pixels, colour swaps, duplicate cursors, freezes or crashes.

4. Recovery
-----------
Copy D:/MINT/MONO.CNF over MINT.CNF and reboot for the working monochrome
GUI, or use SHELL.CNF for the internal shell. fVDI is not in C:/AUTO, so
changing this one configuration file disables the experiment.
If DDR firmware fails to boot, flash the SRAM-only recovery ROM with the
same vendor command, substituting emutos-a2560m-sram.rom as the filename.

Implementation notes
--------------------
Framebuffer: 0x3F800000, reserved 8 MiB; general DDR RAM:
0x00800000..0x3F7FFFFF (1008 MiB). RGB565 is native big-endian, stride
2560 bytes at full width. The driver hides TOSGRAPH/text and disables the
hardware pointer while using fVDI's software cursor. It restores the
previous display state on physical workstation close.

This revision enables CPU data caching with write-through RAM mappings.
Large RGB565 copy operations and solid replacement fills use VDMA. Other
raster operations use CPU drawing. Cache synchronization surrounds DMA;
the original TTR/cache state is restored on workstation close. No MDMA,
SDMA or asynchronous DMA interrupt handling is enabled.

After copying this revision, run D:/MINT/FVDI/DMATEST.TOS from TeraDesk or
the shell. Expect PASS for cached writes, copy/fill, cached readback and
both overlap directions. Scratch is in reserved off-screen DDR; the test
also works while fVDI is installed. Then test window dragging, scrolling,
redraw, mouse shapes and menus. Check for VDMA errors on the console.
Video Options now lists Foenix full/half RGB565 and monochrome at current
timing. Mode changes remain FVDI.SYS configuration before starting AES.

Host tests passed for memory exclusion, failed-probe behavior, video state,
mode/stride/addressing and restoration. Physical testing on 2026-10-17
passed RAMTEST (4 MiB), all eight RGB565 bars with monochrome restoration,
and colour XaAES/TeraDesk startup, directory/dialog/text-viewer rendering.
The previous CPU-only driver dragged slowly; the current cache/VDMA
driver passed the performance check below. Longer stress testing remains
outstanding.
See IMPLEMENT.TXT and MINT/SOURCE/FVDI.TXT for source and rebuild details.

Cache/VDMA physical validation passed on 2026-10-17: DMATEST confirmed
cached CPU writes, copy/fill, cached readback and both overlap directions.
User reports window dragging is now very responsive with no corruption.
This is a qualitative observation, not a numerical performance benchmark.
When launched under the colour desktop, diagnostic console text may remain
in the hidden legacy monochrome buffer. Use shell recovery for visible text.
Video Options visually passed: current 1280x960 16 bpp; valid RGB565
1280x960/640x480 and monochrome 1280x960. Half-mode switching not tested.
