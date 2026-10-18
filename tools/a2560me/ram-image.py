#!/usr/bin/env python3
"""Create a vendor-debug RAM boot S-record with matching reset vectors.
GPL-2.0-or-later; see doc/license.txt.
"""
from pathlib import Path
import struct
import sys

source=Path(sys.argv[1]); out=Path(sys.argv[2]); data=source.read_bytes()
if len(data)!=512*1024 or struct.unpack_from('>I',data,4)[0]!=0x00100008:
    raise SystemExit('Refusing RAM upload: expected 512 KiB image linked at 0x00100000')

def record(address,payload):
    body=address.to_bytes(4,'big')+payload
    count=len(body)+1
    return 'S3'+bytes([count]).hex().upper()+body.hex().upper()+f'{(~(count+sum(body)))&255:02X}'
lines=[record(0,data[:8])]
lines += [record(0x100000+i,data[i:i+128]) for i in range(0,len(data),128)]
lines += ['S70500100008E2']
out.write_text('\n'.join(lines)+'\n')
print(out)
