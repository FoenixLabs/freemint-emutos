#!/bin/sh
# Build the Foenix-aware TeraDesk Video Options; GPL-2.0-or-later.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$here/../.." && pwd)
work=$(CDPATH= cd -- "$root/.." && pwd)
patch="$here/teradesk-video.patch"
if git -C "$work/teradesk" apply --check "$patch" 2>/dev/null; then
    git -C "$work/teradesk" apply "$patch"
else
    git -C "$work/teradesk" apply --reverse --check "$patch"
fi
make -C "$work/mintlib/include"
make -C "$work/mintlib/syscall"
make -C "$work/mintlib/mintlib"
make -C "$work/mintlib" all-here BASE_FLAVOURS=m68020 WITH_FASTCALL=no \
    CFLAGS_m68020='-m68060 -msoft-float'
make -C "$work/mintlib/build/m68020" -j4 libc.a crt0.o CFLAGS-syscall.c=-std=gnu99
make -C "$work/gemlib" .lib68020-60/libgem.a CC="$here/cc.py" \
    CFLAGS_68020-60='-m68060 -msoft-float' -j4
make -C "$work/teradesk" clean
make -C "$work/teradesk" -j4 CC="$here/cc.py" \
    CFLAGS='-m68060 -msoft-float -Os -fomit-frame-pointer -Ilibrary/xdialog -Ilibrary/utility -I../gemlib -Wall -Wextra' \
    LDFLAGS='-nostdlib -Wl,--stack,32k -s ../mintlib/build/m68020/crt0.o' \
    LIBS='-L../gemlib/.lib68020-60 -L../mintlib/build/m68020 -Wl,--start-group -lgem -lc -lgcc -Wl,--end-group'
cp "$work/teradesk/desktop.prg" "$root/drive_d/DESKTOP/DESKTOP.PRG"
cp "$patch" "$root/drive_d/MINT/SOURCE/TERAVID.PAT"
cp "$here/rebuild-desktop.sh" "$root/drive_d/MINT/SOURCE/TDBUILD.SH"
