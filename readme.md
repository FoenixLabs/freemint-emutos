# EmuTOS for A2560Me

Firmware fork for the Foenix A2560Me 68LC/EC060 board (66.67 MHz, no FPU).
The integrated FreeMiNT/fVDI/XaAES/TeraDesk system lives at:
https://github.com/FoenixLabs/freemint-agent-workspace.

This repository owns BIOS/GEMDOS/VDI firmware, the Foenix HAL, the DDR
allocation contract and firmware tests. The fVDI repository owns the colour
driver; the integration repository owns drive templates, cross-component
builds, vendor flashing and release packaging.

The original imported Foenix history and all validated changes are preserved
at tag a2560me-validated-20261017. Official EmuTOS VERSION_1_4 ancestry is
recorded by a merge without replacing the imported Foenix working tree.

Use the integration build for reproducible release artifacts. Standalone
`./compile.sh` needs MiNTLib headers in sibling mintlib/ and builds the
recorded flash (0xFFD00000), RAM (0x00100000), and SRAM-only recovery profiles.
The profile and helpers are under tools/a2560me/. Mutable state must remain
in RAM; firmware data initialized into ROM must remain const.

Upstream documentation: doc/. Foenix background: doc/genxtos.md.
License: GPL-2.0-or-later; see doc/license.txt.
