# Firmware-only build helpers

The release profile is firmware-localconf.h. `../../compile.sh` builds
flash, RAM-test and SRAM-only recovery images. The integration workspace
pins dependencies and verifies these against the physical-test baseline.
The firmware memory-map header must agree with fVDI's allocation contract.
