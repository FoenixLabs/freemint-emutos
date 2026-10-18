#!/bin/sh
# Offline Foenix-aware TeraDesk build from bundled sources; GPL-2.0+.
set -eu
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=${1:-"$PWD/teradesk-build"}
mkdir -p "$work"
work=$(CDPATH= cd -- "$work" && pwd)
for archive in LIBSRC GEMSRC TERASRC; do tar -xzf "$src/$archive.TGZ" -C "$work"; done
python3 - "$work/teradesk/video.c" <<'PYEND'
from pathlib import Path
import sys
p=Path(sys.argv[1]); p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
PYEND
patch -d "$work/teradesk" -p1 < "$src/TERAVID.PAT"
python3 - "$work" <<'PY'
from pathlib import Path
import sys
w=Path(sys.argv[1]); p=w/'desktop-cc'
p.write_text('#!/usr/bin/env python3\nimport os,sys\n'
    'os.execv("/usr/bin/m68k-atari-mint-gcc",["m68k-atari-mint-gcc",'
    '"-isystem",'+repr(str(w/'mintlib/include'))+']+sys.argv[1:])\n')
p.chmod(0o755)
PY
make -C "$work/mintlib/include"
make -C "$work/mintlib/syscall"
make -C "$work/mintlib/mintlib"
make -C "$work/mintlib" all-here BASE_FLAVOURS=m68020 WITH_FASTCALL=no \
    CFLAGS_m68020='-m68060 -msoft-float'
make -C "$work/mintlib/build/m68020" -j4 libc.a crt0.o CFLAGS-syscall.c=-std=gnu99
make -C "$work/gemlib" .lib68020-60/libgem.a CC="$work/desktop-cc" \
    CFLAGS_68020-60='-m68060 -msoft-float' -j4
make -C "$work/teradesk" -j4 CC="$work/desktop-cc" \
    CFLAGS='-m68060 -msoft-float -Os -fomit-frame-pointer -Ilibrary/xdialog -Ilibrary/utility -I../gemlib -Wall -Wextra' \
    LDFLAGS='-nostdlib -Wl,--stack,32k -s ../mintlib/build/m68020/crt0.o' \
    LIBS='-L../gemlib/.lib68020-60 -L../mintlib/build/m68020 -Wl,--start-group -lgem -lc -lgcc -Wl,--end-group'
printf 'Desktop: %s/teradesk/desktop.prg\n' "$work"
