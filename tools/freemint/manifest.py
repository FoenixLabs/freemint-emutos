#!/usr/bin/env python3
"""Refresh checksums after staging a kernel; GPL-2.0-or-later."""
from pathlib import Path
import hashlib
import re

root = Path(__file__).resolve().parents[2]
info = root / 'drive_c/BUILD.TXT'
text = info.read_text()
for actual, label in [('emutos-a2560m.rom', 'emutos-a2560m.rom'),
                      ('drive_c/AUTO/MINT060.PRG', 'AUTO/MINT060.PRG')]:
    digest = hashlib.sha256((root / actual).read_bytes()).hexdigest()
    text = re.sub(r'[0-9a-f]{64}  ' + re.escape(label), digest + '  ' + label, text)
info.write_text(text)
for name in ('drive_c', 'drive_d'):
    folder = root / name
    lines = [hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + str(p.relative_to(folder))
             for p in sorted(folder.rglob('*'))
             if p.is_file() and p.name != 'SHA256.TXT']
    (folder / 'SHA256.TXT').write_text('\n'.join(lines) + '\n')
