#!/bin/sh
# Build the A2560Me first-boot kernel; GPL-2.0-or-later.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$script_dir/../.." && pwd)
work=${1:-"$root/.."}
mkdir -p "$work"
work=$(CDPATH= cd -- "$work" && pwd)
mint_rev=4ef482b68318c9741b512eec2a05349fff6eb716
lib_rev=660081d0937299e2e76f9705148019d972d8b46f
checkout() {
    name=$1 url=$2 revision=$3
    if [ ! -d "$work/$name/.git" ]; then
        git clone "$url" "$work/$name"
    fi
    test "$(git -C "$work/$name" rev-parse HEAD)" = "$revision" ||
        git -C "$work/$name" checkout --detach "$revision"
}
checkout freemint https://github.com/freemint/freemint.git "$mint_rev"
checkout mintlib https://github.com/freemint/mintlib.git "$lib_rev"
if git -C "$work/freemint" apply --check "$script_dir/a2560me.patch" 2>/dev/null; then
    git -C "$work/freemint" apply "$script_dir/a2560me.patch"
else
    git -C "$work/freemint" apply --reverse --check "$script_dir/a2560me.patch"
fi
make -C "$work/mintlib/include" features.h linker.h syscall-list.h
# Clean after changing target flags. Serial make avoids upstream's shared
# arch/magic generator being invoked concurrently for the same output.
make -C "$work/freemint/sys" clean
# Build the host generator before overriding CC for the cross build.
make -C "$work/freemint/sys/buildinfo"
make -C "$work/freemint/sys" 060 -j1 CC="$script_dir/cc.py" MMU_SUPPORT= \
    M68K_ATARI_MINT_CFLAGS="-DMACHINE_A2560M -DOLDTOSFS -msoft-float -isystem $work/mintlib/include"
mkdir -p "$root/drive_c/AUTO" "$root/drive_d/MINT/SOURCE"
cp "$work/freemint/sys/.compile_060/mint060.prg" "$root/drive_c/AUTO/MINT060.PRG"
# Matching source, headers, licenses and recipe travel with the binary.
git -C "$work/freemint" archive --format=tar --prefix=freemint/ "$mint_rev" |
    gzip -n > "$root/drive_d/MINT/SOURCE/MINTSRC.TGZ"
git -C "$work/mintlib" archive --format=tar --prefix=mintlib/ "$lib_rev" |
    gzip -n > "$root/drive_d/MINT/SOURCE/LIBSRC.TGZ"
cp "$script_dir/a2560me.patch" "$root/drive_d/MINT/SOURCE/BOARD.DIF"
cp "$script_dir/cc.py" "$root/drive_d/MINT/SOURCE/CC.PY"
cp "$script_dir/rebuild.sh" "$root/drive_d/MINT/SOURCE/BUILD.SH"
cp "$script_dir/README.TXT" "$root/drive_d/MINT/SOURCE/README.TXT"
python3 "$script_dir/manifest.py"
sha256sum "$root/drive_c/AUTO/MINT060.PRG"
