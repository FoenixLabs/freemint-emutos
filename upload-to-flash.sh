#!/bin/sh
# Vendor debug-protocol v2 flasher; block 2 of the 512 KiB layout.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$root"
image=${1:-emutos-a2560m.rom}
python3 tools/a2560me_dbg.py --port "${PORT:-/dev/ttyUSB1}" --flash "$image" --block 2 --layout 512k
