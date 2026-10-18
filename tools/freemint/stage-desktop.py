#!/usr/bin/env python3
"""Extract only the required desktop files; GPL-2.0-or-later."""
from pathlib import Path
from zipfile import ZipFile
import sys

out = Path(__file__).resolve().parents[2] / 'drive_d/DESKTOP'
files = {'DESKTOP.PRG': 'DESKTOP.PRG', 'DESKTOP.RSC': 'DESKTOP.RSC',
         'ICONS.RSC': 'ICONS.RSC', 'CICONS.RSC': 'CICONS.RSC',
         'DOC/COPYING': 'COPYING', 'README.TXT': 'UPSTREAM.TXT',
         'DOC/TERADESK.HYP': 'TERADESK.HYP', 'DOC/TERADESK.REF': 'TERADESK.REF'}
with ZipFile(sys.argv[1]) as archive:
    for source, target in files.items():
        (out / target).write_bytes(archive.read(source))
