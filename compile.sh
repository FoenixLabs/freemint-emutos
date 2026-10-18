#!/bin/sh
# A2560Me release profile: DDR flash, RAM test and SRAM recovery ROMs.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$root/tools/a2560me/build-firmware.sh" "$@"
