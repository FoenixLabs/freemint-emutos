#!/bin/sh
# Build SRAM recovery, DDR RAM-test and final DDR flash images; GPL-2.0+.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$script_dir/../.." && pwd)
cd "$root"
# Preserve local overrides; a release build must use its recorded profile.
if [ -f localconf.h ]; then
    if ! cmp -s localconf.h "$script_dir/firmware-localconf.h"; then
        echo 'localconf.h differs from the release profile; preserve/review it before a release build.' >&2
        exit 1
    fi
else
    cp "$script_dir/firmware-localconf.h" localconf.h
fi
make -C "$root/../mintlib/include" features.h linker.h syscall-list.h
mkdir -p obj logs/fvdi/firmware-before
for name in emutos-a2560m.rom emutos.img emutos.map; do
    if [ -f "$name" ]; then cp "$name" "logs/fvdi/firmware-before/$name"; fi
done
complete=0
cleanup() {
    if [ "$complete" != 1 ]; then
        make clean > logs/fvdi/firmware-cleanup.log 2>&1 || true
        for name in emutos-a2560m.rom emutos.img emutos.map; do
            if [ -f "logs/fvdi/firmware-before/$name" ]; then
                cp "logs/fvdi/firmware-before/$name" "$name"
            fi
        done
    fi
}
trap cleanup EXIT
make clean > logs/fvdi/sram-clean.log 2>&1
make UNIQUE=us a2560m -j4 "$@" CC="$root/tools/fvdi/cc.py" \
    A2560M_DEFS=-DCONF_WITH_A2560M_DDR=0 > logs/fvdi/sram-build.log 2>&1
cp emutos-a2560m.rom logs/fvdi/emutos-sram.rom
make clean > logs/fvdi/ram-clean.log 2>&1
make UNIQUE=us a2560m -j4 "$@" CC="$root/tools/fvdi/cc.py" \
    A2560M_DEFS=-DA2560M_RAM_IMAGE > logs/fvdi/ram-build.log 2>&1
cp emutos-a2560m.rom logs/fvdi/emutos-ram.rom
cp emutos.map logs/fvdi/emutos-ram.map
python3 "$script_dir/ram-image.py" logs/fvdi/emutos-ram.rom logs/fvdi/emutos-ddr-ram.srec
make clean > logs/fvdi/flash-clean.log 2>&1
make UNIQUE=us a2560m -j4 "$@" CC="$root/tools/fvdi/cc.py" \
    A2560M_DEFS= > logs/fvdi/flash-build.log 2>&1
cp logs/fvdi/emutos-sram.rom emutos-a2560m-sram.rom
cp logs/fvdi/emutos-ram.rom emutos-a2560m-ram.rom
sha256sum emutos-a2560m.rom emutos-a2560m-ram.rom emutos-a2560m-sram.rom
complete=1
