#!/bin/sh
# Stage XaAES and TeraDesk for the A2560Me monochrome VDI; GPL-2.0-or-later.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$script_dir/../.." && pwd)
work=${1:-"$root/.."}
work=$(CDPATH= cd -- "$work" && pwd)
require_repo() {
    name=$1 revision=$2
    if [ ! -d "$work/$name/.git" ]; then
        git clone "https://github.com/freemint/$name.git" "$work/$name"
        git -C "$work/$name" checkout --detach "$revision"
    fi
    if [ "$(git -C "$work/$name" rev-parse HEAD)" != "$revision" ]; then
        printf 'Expected %s at %s; keeping your checkout unchanged.\n' "$name" "$revision" >&2
        exit 1
    fi
}
require_repo freemint 4ef482b68318c9741b512eec2a05349fff6eb716
require_repo mintlib 660081d0937299e2e76f9705148019d972d8b46f
require_repo gemlib 68f94dabdffbcd7dc1bda762dc97bdccf1ad9488
require_repo teradesk 8035b6e157bd34cb2bd72a26473990c7711501de
make -C "$work/mintlib/include" features.h linker.h syscall-list.h
make -C "$work/gemlib" .lib68020-60.short/libgem.a -j4 \
    CFLAGS="-O2 -msoft-float -isystem $work/mintlib/include"
xa="$work/freemint/xaaes/src.km"
flags="-DMACHINE_A2560M -DOLDTOSFS -msoft-float -I$work/gemlib -isystem $work/mintlib/include -L$work/gemlib/.lib68020-60.short"
# Rebuild all GUI objects with the board's no-FPU compiler settings.
make -C "$xa" clean
make -C "$xa" 02060 -j4 CPU_02060=060 CC="$script_dir/cc.py" \
    M68K_ATARI_MINT_CFLAGS="$flags"
make -C "$xa/xaloader" 02060 -j4 CPU_02060=060 CC="$script_dir/cc.py" \
    M68K_ATARI_MINT_CFLAGS="$flags"
make -C "$xa/adi/whlmoose" 02060 -j4 CPU_02060=060 CC="$script_dir/cc.py" \
    M68K_ATARI_MINT_CFLAGS="$flags"
mkdir -p "$work/downloads" "$root/drive_d/MINT/XAAES" "$root/drive_d/DESKTOP" "$root/drive_d/MINT/SOURCE"
archive="$work/downloads/teradesk-4.08-8035b6e1.zip"
if [ ! -f "$archive" ]; then
    curl -fL --connect-timeout 10 --max-time 120 \
        https://atari.joska.no/snapshots/teradesk/teradesk-4.08-8035b6e1.zip -o "$archive"
fi
printf '%s  %s\n' 288d2c961be3fa512ae89c09a02bcab9448a2cdb0a0d5213f95494f743c0ca4c "$archive" | sha256sum -c -
cp "$xa/.compile_02060/xaaes020.km" "$root/drive_d/MINT/XAAES/XAAES020.KM"
cp "$xa/xaloader/.compile_02060/xaloader.prg" "$root/drive_d/MINT/XAAES/XALOADER.PRG"
cp "$xa/adi/whlmoose/.compile_02060/moose.adi" "$root/drive_d/MINT/XAAES/MOOSE.ADI"
for name in xaaes xaaeswdg xa_xtobj; do
    upper=$(printf '%s' "$name" | tr '[:lower:]' '[:upper:]')
    cp "$xa/$name.rsc" "$root/drive_d/MINT/XAAES/$upper.RSC"
done
python3 "$script_dir/stage-desktop.py" "$archive"
# Replace stock executable with the Foenix-aware Video Options build.
"$root/tools/fvdi/build-desktop.sh"
cp "$archive" "$root/drive_d/MINT/SOURCE/TERABIN.ZIP"
for name in gemlib teradesk; do
    case "$name" in gemlib) out=GEMSRC.TGZ ;; teradesk) out=TERASRC.TGZ ;; esac
    git -C "$work/$name" archive --format=tar --prefix="$name/" HEAD |
        gzip -n > "$root/drive_d/MINT/SOURCE/$out"
done
# The existing MINTSRC.TGZ includes XaAES/loader/moose at this same revision.
cp "$script_dir/GUI.TXT" "$root/drive_d/MINT/SOURCE/GUI.TXT"
cp "$script_dir/rebuild-gui.sh" "$root/drive_d/MINT/SOURCE/GUIBUILD.SH"
cp "$script_dir/cc.py" "$root/drive_d/MINT/SOURCE/CC.PY"
python3 "$script_dir/manifest.py"
python3 "$script_dir/verify-gui.py" "$work"
