A2560Me FreeMiNT first-boot build
================================
FreeMiNT: https://github.com/freemint/freemint
Revision: 4ef482b68318c9741b512eec2a05349fff6eb716
MiNTLib (build-time headers): https://github.com/freemint/mintlib
Revision: 660081d0937299e2e76f9705148019d972d8b46f

Host tools: m68k-atari-mint GCC/binutils (built here with GCC 4.6.4),
native GCC, GNU make, Perl, awk, Python 3, patch, tar and gzip.
The cross compiler must be on PATH as m68k-atari-mint-gcc. CC.PY invokes
that compiler through /usr/bin; edit that path if installed elsewhere.

From the EmuTOS repository run tools/freemint/build.sh [build-directory].
The default build directory is the parent A2560ME project directory,
using the persistent freemint/ and mintlib/ Git checkouts.
This downloads missing pinned sources, applies a2560me.patch, builds the 060
kernel and refreshes the staged binary and matching source bundle.
Existing local source changes are retained; no reset or clean -fd is used.
Build-directory paths must not contain spaces (upstream make limitation).

From D:/MINT/SOURCE copied onto a Linux host, run:
    chmod +x CC.PY BUILD.SH
    ./BUILD.SH /tmp/a2560me-freemint-build
This uses the included MINTSRC.TGZ and LIBSRC.TGZ without downloading.
The directory should be new/empty. Result:
    /tmp/a2560me-freemint-build/freemint/sys/.compile_060/mint060.prg

Board build: -DMACHINE_A2560M -m68060 -mshort -msoft-float for C, no MMU
support. -DOLDTOSFS keeps C: on EmuTOS GEMDOS, while FS_NEWFATFS=D
enables the native FAT32 driver only on D:. This avoids rejecting C:
when it has 65523 FAT16 clusters (the native driver rejects >=65519).
Handwritten assembly retains upstream guarded FPU save/restore
instructions, but board FPU detection returns zero and they are skipped.
CC.PY removes -msoft-float for .S only so these instructions assemble;
it does not permit compiler-generated floating point in interrupt C.

Patch changes: report no on-CPU FPU or Atari SFP-004 coprocessor without
probing either; cpu_stop enables interrupts without executing STOP;
cpu_lpstop does not execute LPSTOP. Other machines keep upstream behavior.
Memory protection is compiled out for first bring-up. Do not add MEM_PROT
to MINT.INI for this build; that option only exists in MMU-enabled builds.

Licensing: the archives include all upstream notices and licenses.
See freemint/COPYING and freemint/COPYING.GPL, COPYING.LGPL and COPYING.MiNT, plus the notices in
each source file; MiNTLib has its own COPYING/COPYING.LIB and exceptions.
The board patch and scripts in this repository are GPL-2.0-or-later.
Build timestamps can change the resulting binary hash on a later rebuild.
This kernel is an experimental board bring-up build, not an official
FreeMiNT release. The user reports basic shell/keyboard and C:/D: file
persistence tests passed after fixing the FAT16 format.

For the accelerated colour GUI, see GUI.TXT, build-gui.sh and
../fvdi/build.sh. Colour mode requires the matching DDR-aware EmuTOS ROM;
MONO.CNF retains the validated monochrome recovery configuration.
