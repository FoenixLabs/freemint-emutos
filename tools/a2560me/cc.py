#!/usr/bin/env python3
"""Cross compiler wrapper for the A2560Me no-FPU fVDI build (GPL-2.0+)."""
import os
from pathlib import Path
import sys
headers = Path(__file__).resolve().parents[3] / 'mintlib/include'
args = sys.argv[1:]
if any(arg.endswith('.c') for arg in args):
    args = ['-msoft-float'] + args
args = ['-isystem', str(headers)] + args
os.execv('/usr/bin/m68k-atari-mint-gcc', ['m68k-atari-mint-gcc'] + args)
