#!/bin/sh
# A2560Me temporary RAM boot using the vendor's verified debug protocol.
# The flash is unchanged. Build with tools/fvdi/build-firmware.sh first.
set -eu
image=${1:-emutos-a2560m-ram.rom}
mkdir -p logs/fvdi
python3 tools/fvdi/ram-image.py "$image" logs/fvdi/emutos-ddr-ram.srec
python3 tools/a2560me_dbg.py --port /dev/ttyUSB1 \
    --run logs/fvdi/emutos-ddr-ram.srec --reset-first
