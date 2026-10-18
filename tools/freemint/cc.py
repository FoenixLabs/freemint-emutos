#!/usr/bin/env python3
"""Keep C soft-float while allowing guarded FPU instructions in upstream .S.

Distributed under GPL version 2 or later; see doc/license.txt.
"""
import os,sys
args=sys.argv[1:]
if any(x.endswith('.S') for x in args):
    args=[x for x in args if x != '-msoft-float']
os.execv('/usr/bin/m68k-atari-mint-gcc',['m68k-atari-mint-gcc']+args)
