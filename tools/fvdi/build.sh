#!/bin/sh
# Build and stage fVDI's A2560Me RGB565 driver and diagnostics; GPL-2.0+.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$script_dir/../.." && pwd)
work=$(CDPATH= cd -- "$root/.." && pwd)
repo="$work/fvdi"
revision=2d51380bfa177c6f60565e6e246c4881ce9eaacb
if [ ! -d "$repo/.git" ]; then
    git clone https://github.com/freemint/fvdi.git "$repo"
    git -C "$repo" checkout --detach "$revision"
fi
if [ "$(git -C "$repo" rev-parse HEAD)" != "$revision" ]; then
    printf 'fVDI revision differs; preserving the checkout. Expected %s\n' "$revision" >&2
    exit 1
fi
src="$repo/fvdi"
driver="$src/drivers/a2560me"
mkdir -p "$driver" "$root/drive_d/MINT/FVDI" "$root/logs/fvdi"
# Export the same memory map used by the firmware; never allocate VRAM as RAM.
cp "$root/foenix/a2560me_memory.h" "$script_dir/a2560me/a2560me_memory.h"
cp "$script_dir/a2560me/"* "$driver/"
make -C "$src/utility/conv2gas" CC=gcc NATIVE_CC=gcc
make -C "$src/utility/structer" CC=gcc NATIVE_CC=gcc
make -C "$src/engine" clean
make -C "$src/engine" CPU=060 CC="$script_dir/cc.py" -j4
make -C "$driver" clean
make -C "$driver" CPU=060 CC="$script_dir/cc.py" -j4
cp "$src/engine/fvdi_gnu.prg" "$root/drive_d/MINT/FVDI/FVDI.PRG"
cp "$driver/a2560me.sys" "$root/drive_d/MINT/FVDI/A2560ME.SYS"
# Small diagnostics have no C runtime or FPU requirements.
probe_build="$root/logs/fvdi/probe-build"
mkdir -p "$probe_build"
cc="$script_dir/cc.py"
"$cc" -m68060 -mshort -c "$script_dir/probe/start.S" -o "$probe_build/start.o"
for name in guipat ramtest dmatest; do
    "$cc" -m68060 -mshort -Os -fomit-frame-pointer -Wall -Wextra \
        -Werror -I"$driver" -c "$script_dir/probe/$name.c" -o "$probe_build/$name.o"
    library=$("$cc" -m68060 -mshort -print-libgcc-file-name)
    upper=$(printf '%s' "$name" | tr '[:lower:]' '[:upper:]')
    m68k-atari-mint-ld -s --entry=_start --mprg-flags=0 \
        -o "$root/drive_d/MINT/FVDI/$upper.TOS" "$probe_build/start.o" \
        "$probe_build/$name.o" "$library"
done
python3 "$script_dir/source-bundle.py"
python3 "$root/tools/freemint/manifest.py"
python3 "$script_dir/verify.py"
