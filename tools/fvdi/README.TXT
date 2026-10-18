A2560Me fVDI / DDR3 accelerated RGB565 driver
======================================

Source: https://github.com/freemint/fvdi
Pinned upstream revision: 2d51380bfa177c6f60565e6e246c4881ce9eaacb
Persistent checkout: ../fvdi/ (beside the EmuTOS repository).
Driver source of record: tools/fvdi/a2560me/ in the EmuTOS repository.
build.sh exports it into fvdi/fvdi/drivers/a2560me/ before compiling.
New glue is GPL-2.0-or-later. Generic rendering retains its upstream
public-domain and GPL notices. Full source is in FVDISRC.TGZ.

Hardware reference rev 1.8, GUI engine pages 69-71:
- DDR3 CPU-visible range 0x00800000..0x3FFFFFFF; low 8 MiB hidden by SRAM.
- 1008 MiB alternate RAM: 0x00800000..0x3F7FFFFF.
- Reserved 8 MiB video region: 0x3F800000..0x3FFFFFFF; never Maddalt RAM.
- FVRM cookie value 0x3F800000 advertises the reservation. Driver and
  GUIPAT refuse old firmware without this cookie.
- Full mode: 1280x960 RGB565, stride 2560 bytes, GUI CTRL=13.
- If existing video timing is 1024 lines, it uses 1280x1024 instead.
- Optional 'half' driver option: 640x480/512, stride 1280, CTRL=5.
- ADDR is the CPU/DDR byte address, not divided by four or 32.
- Master graphics bit 2 selects GUI; TOSGRAPH/MemText/text are hidden.
- Existing video timing is preserved; no SiI9022 programming is performed.
- 32-bit accesses for GUI/master registers; 16-bit mouse-control accesses.

Rendering reuses fVDI's CPU-readable big-endian RGB565 routines for
pixels, lines, patterned fills, expansion, raster operations and cursor.
Large (at least 1024 pixels) replacement copies and solid replacement
fills use the VDMA, with CPU fallback for SRAM buffers, small operations,
patterns and other raster operations. Overlapping copies use descending
segments and negative strides where needed. Hardware pointer is disabled
while the software cursor is active; display registers are saved/restored.

Cache policy: cache RAM 0x00000000..0x3FFFFFFF write-through in user and
supervisor mode, keep CPU D-cache enabled, and explicitly inhibit high
I/O via a second TTR (the FPGA also asserts TCI for MMIO). CPU L1 and FPGA
L2 both write through, so scanout sees CPU writes. Initial CACR and both
DTTs are restored on close. MMU-enabled configurations are refused.
XaAES CACR restoration is handled at each rendering entry. TTR changes
push/invalidate first; unchanged entries do not flush. Around synchronous
VDMA jobs, mask interrupts, push/invalidate the CPU D-cache before START,
and invalidate it after DONE. The FPGA handles its L2 destination
invalidations before DONE. Polling is bounded, errors abort and disable
acceleration, and a partially completed operation is never replayed.
No DMA IRQs, descriptor lists, MDMA or SDMA are used in this version.
DDR endian inversion must be off and GGE must not own the GUI port.

VDMA implementation: Hardware Reference rev 1.8 pp. 84-87, MMIO at
0xFEC0C200, longword writes, 16-bit pixels, source A copy (LF F0) or
constant A fill. Descriptor addresses are CPU/DDR byte addresses. Driver
checks rectangle bounds and alignment before starting. The diagnostic
uses reserved video scratch at 0x3FC00000, outside the visible framebuffer.

TeraDesk Video Options is patched for _VDO=0xF258: actual VDI dimensions,
full/half RGB565 at current 960/1024-line timing, and monochrome. It does
not expose Atari shifter modes or pretend live Setscreen switching works.
Select full/half in FVDI.SYS before starting AES. Rebuild/stage desktop with
tools/fvdi/build-desktop.sh. The patch is teradesk-video.patch. Bundled
TERAVID.PAT + TDBUILD.SH rebuild offline from TERASRC/GEMSRC/LIBSRC.

Build: tools/fvdi/build.sh from the EmuTOS repository. Prerequisites:
m68k-atari-mint GCC/binutils, native GCC, make, Perl, flex, bison, Python 3
and the persistent MiNTLib headers/source used by our FreeMiNT build.
No FreeType or floating-point code is used. Engine uses its native 32-bit
C int ABI; driver/probes use -mshort as required by the fVDI driver code.
All C is -m68060 -msoft-float. Assembly contains no STOP or FPU code.

Offline rebuild: copy MINT/SOURCE to a Linux cross-build host, chmod +x
FVBUILD.SH, then ./FVBUILD.SH /path/to/new-empty-directory. It extracts
FVDISRC.TGZ and LIBSRC.TGZ and builds the engine and driver. Diagnostic
sources and their minimal startup are included under a2560me-probe/.
Building diagnostics uses -m68060 -mshort -Os -msoft-float, links start.o
and the selected C object with libgcc, entry _start and PRG flags zero.

Firmware: CONF_WITH_A2560M_DDR enables fixed-map alternate RAM after a
non-destructive boundary pattern check. Registration failure does not
advertise FVRM. Readability is guarded where EmuTOS bus-error probing is
configured; otherwise the fixed, documented A2560Me DDR aperture is used.
The boundary test is not a complete 1 GiB RAM stress test. RAMTEST.TOS
checks a 4 MiB allocated region; GUIPAT.TOS tests scanout and restoration.

Host verification covers reservations, failed probes, content restoration,
video/cache save/restore, modes, byte addresses, stride, binary headers
and absence of FPU/STOP instructions. A physical RAM boot passed: FreeMiNT reported FastTotal 1,031,632 kB
and the FVRM cookie was 0x3F800000. The previous driver passed RGB565
bars/restoration, colour desktop and physical mouse tests; dragging was
slow. This cache/VDMA revision passed the physical DMATEST checks on
2026-10-17; the user reports responsive dragging with no corruption. Follow D:/MINT/FVDI/README.TXT in order.

DMATEST.TOS checks CPU cached writes -> DMA -> cached readback, fill
and overlapping copies in both directions. Host tests: tests/fvdi/dma.py.

Physical Video Options verification passed at 1280x960 16 bpp: full/half
RGB565 and monochrome at the current timing, with no Atari shifter modes.
Half-mode switching and long-duration stress tests remain unperformed.

Permanent flash installation passed on 2026-10-17: vendor programming,
byte-for-byte readback and normal colour desktop boot. compile.sh uses
the recorded firmware-localconf.h release profile for future builds.
