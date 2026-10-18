#!/bin/sh
# Rebuild GUI modules from the included source archives; GPL-2.0-or-later.
set -eu
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=${1:-"$PWD/gui-build"}
mkdir -p "$work"
work=$(CDPATH= cd -- "$work" && pwd)
for archive in MINTSRC LIBSRC GEMSRC TERASRC; do
    tar -xzf "$src/$archive.TGZ" -C "$work"
done
patch -d "$work/freemint" -p1 < "$src/BOARD.DIF"
make -C "$work/mintlib/include" features.h linker.h syscall-list.h
make -C "$work/gemlib" .lib68020-60.short/libgem.a -j4 \
    CFLAGS="-O2 -msoft-float -isystem $work/mintlib/include"
flags="-DMACHINE_A2560M -DOLDTOSFS -msoft-float -I$work/gemlib -isystem $work/mintlib/include -L$work/gemlib/.lib68020-60.short"
make -C "$work/freemint/sys/libkern" libkern060.a -j4 CC="$src/CC.PY" \
    M68K_ATARI_MINT_CFLAGS="$flags"
xa="$work/freemint/xaaes/src.km"
for subdir in . xaloader adi/whlmoose; do
    make -C "$xa/$subdir" 02060 -j4 CPU_02060=060 CC="$src/CC.PY" \
        M68K_ATARI_MINT_CFLAGS="$flags"
done
mkdir -p "$work/gui-stage/XAAES" "$work/gui-stage/DESKTOP"
cp "$xa/.compile_02060/xaaes020.km" "$work/gui-stage/XAAES/XAAES020.KM"
cp "$xa/xaloader/.compile_02060/xaloader.prg" "$work/gui-stage/XAAES/XALOADER.PRG"
cp "$xa/adi/whlmoose/.compile_02060/moose.adi" "$work/gui-stage/XAAES/MOOSE.ADI"
for name in xaaes xaaeswdg xa_xtobj; do
    cp "$xa/$name.rsc" "$work/gui-stage/XAAES/$name.rsc"
done
python3 - "$src/TERABIN.ZIP" "$work/gui-stage/DESKTOP" <<'PY'
from zipfile import ZipFile
from pathlib import Path
import sys
with ZipFile(sys.argv[1]) as z:
    for name in ('DESKTOP.PRG', 'DESKTOP.RSC', 'ICONS.RSC', 'CICONS.RSC'):
        (Path(sys.argv[2]) / name).write_bytes(z.read(name))
PY
# The source bundle includes the Foenix Video Options desktop overlay.
if [ -f "$src/TDBUILD.SH" ]; then
    sh "$src/TDBUILD.SH" "$work/desktop-build"
    cp "$work/desktop-build/teradesk/desktop.prg" "$work/gui-stage/DESKTOP/DESKTOP.PRG"
fi
printf 'GUI output: %s/gui-stage\n' "$work"
