/* Minimal TOS diagnostic startup; GPL-2.0-or-later. */
        .text
        .globl _start
_start:
        lea     _stack_end,sp
        jsr     _probe_main
        move.w  d0,-(sp)
        move.w  #0x4c,-(sp)
        trap    #1
        .bss
        .even
_stack:
        .space  16384
_stack_end:
