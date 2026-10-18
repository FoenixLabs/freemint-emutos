#!/bin/sh
# Rebuild from the matching source package on a Linux cross-build host.
# GPL-2.0-or-later.
set -eu
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=${1:-"$PWD/freemint-build"}
mkdir -p "$work"
work=$(CDPATH= cd -- "$work" && pwd)
tar -xzf "$src/MINTSRC.TGZ" -C "$work"
tar -xzf "$src/LIBSRC.TGZ" -C "$work"
patch -d "$work/freemint" -p1 < "$src/BOARD.DIF"
make -C "$work/mintlib/include" features.h linker.h syscall-list.h
# Build the host generator before overriding CC for the cross build.
make -C "$work/freemint/sys/buildinfo"
make -C "$work/freemint/sys" 060 -j1 CC="$src/CC.PY" MMU_SUPPORT= \
    M68K_ATARI_MINT_CFLAGS="-DMACHINE_A2560M -DOLDTOSFS -msoft-float -isystem $work/mintlib/include"
printf 'Kernel: %s/freemint/sys/.compile_060/mint060.prg\n' "$work"
