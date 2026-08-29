| Exports ---------------------------------------------------------------------
    .GLOBAL _a2560_run_calibration
    .GLOBAL _a2560_irq_calibration

#include "foenix.h"

#define TIMER0_MASK (1 << (INT_TIMER0 & 0x0f))


// returns the number of tight loops done during the calibration time, or -1 if CPU went too fast
_a2560_run_calibration: // Calibration loop
    move.l d2,-(sp)
    clr.l  d0  // Tight loop iterations (de)counter (so to match delay_loop() 
    clr.w  d2  // 
    
cal_loop: // Kind of replicate asm.h's delay_loop() function (though it uses jpl rather than jne)
    // We're using jne so we can use the full 32bit range rather than 31bis. Less chances of this
    // breaking if the CPU is too fast.
    subq.l  #1,d0
    jne     cal_loop // asm.h uses jpl but it should be the same speed

    // If we're here, either the timer interrupted us, or the CPU was too fast and decounted
    // faster than the calibration time.
    
    tst.w   d2 // who interrupted the loop ?
    beq.s   cpu_too_fast

    // the timer interrupted the loop
    neg.l   d1    // cal_loop is a decounter
    move.l  d1,d0 // return value
    move.l  (sp)+,d2
    rts
cpu_too_fast:
    moveq   #-1,d0 // return error code
    move.l  (sp)+,d2
    rts


_a2560_irq_calibration: // Timer 0 handler used for calibration loop, equivalent of handle_timer in delayasm.S
    move.w #TIMER0_MASK,IRQ_MASK_GRP1  // Acknowledge interrupt
    move.l d0,d1   // save tight loop counter
    move.l #2,d0   // make the cal_loop abort "soon"
    scc    d2      // tell that the timer interrupted the loop
    rte
