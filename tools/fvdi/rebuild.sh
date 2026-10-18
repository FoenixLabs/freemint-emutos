#!/bin/sh
# Offline fVDI rebuild from the matching source bundle; GPL-2.0-or-later.
set -eu
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=${1:-"$PWD/fvdi-build"}
mkdir -p "$work"
work=$(CDPATH= cd -- "$work" && pwd)
tar -xzf "$src/FVDISRC.TGZ" -C "$work"
tar -xzf "$src/LIBSRC.TGZ" -C "$work"
make -C "$work/mintlib/include" features.h linker.h syscall-list.h
# The fVDI Makefiles call CC for both preprocessing and compilation.
# This local wrapper supplies headers also for the generated structure tables.
python3 - "$work" <<'PY'
from pathlib import Path
import sys
w=Path(sys.argv[1]); p=w/'fvdi-cc'
p.write_text('#!/usr/bin/env python3\nimport os,sys\na=sys.argv[1:]\n'
    'a=(["-msoft-float"] if any(s.endswith(".c") for s in a) else [])+a\n'
    'os.execv("/usr/bin/m68k-atari-mint-gcc",["m68k-atari-mint-gcc",'
    '"-isystem",'+repr(str(w/'mintlib/include'))+']+a)\n')
p.chmod(0o755)
PY
base="$work/fvdi/fvdi"
make -C "$base/utility/conv2gas" CC=gcc NATIVE_CC=gcc
make -C "$base/utility/structer" CC=gcc NATIVE_CC=gcc
make -C "$base/engine" CPU=060 CC="$work/fvdi-cc" -j4
make -C "$base/drivers/a2560me" CPU=060 CC="$work/fvdi-cc" -j4
printf 'Engine: %s/engine/fvdi_gnu.prg\nDriver: %s/drivers/a2560me/a2560me.sys\n' "$base" "$base"
