#!/usr/bin/env python3
"""a2560me_dbg.py - host tool for the A2560Me debug protocol v2 (DEBUG_REFORGE_PLAN.md).

    request : 5A SEQ CMD ATTR ADDR(4, MSB first) SIZE(2, MSB first) [payload] CRC16(2, MSB first)
    reply   : A5 SEQ STATUS(2) payload CRC16    (data)       B5 SEQ STATUS(2) CRC16    (status only)
    CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over every byte before it. 8 Mbit/s 8N1 (build 78 only: 6 Mbit/s, use --baud 6000000).

Commands (FPGA build 75: stage 1, build 76+: stage 2 memory access):
    rev, status, ext, hold, release, reset                         (stage 1)
    --dump ADDR --count N [--out FILE]                             read memory (hex listing, or raw to FILE)
    --load FILE --address ADDR                                     write a binary file into memory
    --srec FILE                                                    write an S-record file into memory
    --run FILE                                                     hold the CPU, load (binary: --address, S-record:
                                                                   its addresses), verify, release
    flashid                                                        the flash chips' IDs (build 82+, CPU held)
    --flash FILE --block N [--layout 512k|1m|2m|4m]                write an image into the boot flash (or --address):
                                                                   erases only what it covers, programs, verifies,
                                                                   then system reset (--no-reset keeps the CPU held)
Build 85+ (debug stages 4, 5, 8):
    pause, continue, step                                          stop the CPU without a reset (it waits for the bus),
                                                                   let it go, or let it run one bus tenure
    --bp SLOT:ADDR[:KINDS[:MASK]]                                  breakpoint slot 0-3: KINDS = any of c (code fetch),
                                                                   r (data read), w (data write), n (NMI instead of a
                                                                   pause); MASK = low address bits ignored (0-31).
                                                                   --bp-clear SLOT clears a slot. Set before commands.
    report                                                         breakpoint report: state, hit slot / address / cycle
    nmi                                                            monitor stop: level-7 interrupt into the MCP stub
    regs, mstep, mcont                                             monitor stub (MCP 172+): registers, one instruction,
                                                                   continue (mcont also re-arms the breakpoints)
    --peek ADDR[:SIZE] / --poke ADDR:VALUE[:SIZE]                  one access by the CPU inside the stub (registers too)
Memory: SRAM $0000_0000-$007F_FFFF (read / write) and boot flash $FFC0_0000-$FFFF_FFFF (read): up to build 84 only with
the CPU held (the tool holds it for --run; use "hold" before --dump / --load otherwise); build 85+ in any CPU state (the
debug port borrows the bus). DDR3 $0080_0000-$3FFF_FFFF (read / write, build 80+) works while the CPU runs. Blocks of up
to 16384 bytes per frame.
Strict request / reply, no retries: any failure stops the run with exit code 1. The old protocol (FoenixMgr / GenX
Uploader, 6 Mbit/s) keeps working on the same port.

    python a2560me_dbg.py --port COM18 rev status ext
    python a2560me_dbg.py --port COM18 --run foenixmcp_gen2.s68
    python a2560me_dbg.py --port COM18 hold --dump 0 --count 256
"""
import argparse, sys, time

try:
    import serial
except ImportError:
    serial = None

STATUS_BITS = {0: 'CRC_OK', 1: 'CRC_BAD', 2: 'UNKNOWN', 3: 'TOO_BIG', 4: 'RANGE', 5: 'FLASH_ERR', 6: 'TIMEOUT', 7: 'STATE',
               8: 'CPU_HELD', 9: 'CPU_PAUSED', 10: 'BP_HIT', 11: 'BOOT_FAIL', 15: 'EXT'}


def crc16(data, crc=0xFFFF):
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


class DebugPortError(Exception):
    pass


class Progress:
    """A one-line text progress bar:   program  [##########..........]  52%  262144 / 524288 bytes  125 KB/s
    It redraws itself in place (carriage return) and ends with a new line. Quiet when the output is not a terminal."""

    def __init__(self, label, total, unit='bytes', width=30):
        self.label, self.total, self.unit, self.width = label, max(total, 1), unit, width
        self.t0 = time.time()
        self.tty = sys.stdout.isatty()
        self.done = 0
        self.show(0)

    def show(self, done):
        self.done = done
        if not self.tty:
            return
        f = min(done / self.total, 1.0)
        n = int(f * self.width)
        dt = max(time.time() - self.t0, 1e-6)
        rate = ('  %.0f KB/s' % (done / 1024 / dt)) if self.unit == 'bytes' and done else ''
        sys.stdout.write('\r  %-8s [%s%s] %3d%%  %d / %d %s%s   ' % (self.label, '#' * n, '.' * (self.width - n),
                                                                   int(f * 100), done, self.total, self.unit, rate))
        sys.stdout.flush()

    def finish(self):
        if self.tty:
            self.show(self.total)
            sys.stdout.write('\n')
            sys.stdout.flush()


class DebugPortV2:
    def __init__(self, port, baud=8_000_000, timeout=1.0):
        if serial is None:
            raise DebugPortError('pyserial is not installed (pip install pyserial)')
        self.ser = serial.Serial(port, baud, timeout=timeout)
        self.seq = int(time.time()) & 0xFF

    def close(self):
        self.ser.close()

    def transfer(self, cmd, attr=0, addr=0, size=0, payload=b'', reply_len=0, timeout=1.0):
        """One exchange. reply_len = payload bytes of an A5 reply. Returns (status, payload)."""
        self.seq = (self.seq + 1) & 0xFF
        frame = bytes([0x5A, self.seq, cmd, attr]) + addr.to_bytes(4, 'big') + size.to_bytes(2, 'big') + payload
        frame += crc16(frame).to_bytes(2, 'big')
        # Set the time-out BEFORE writing, and only when it changes: on Windows pyserial applies a new time-out by
        # reconfiguring the port, which disturbed the FT4232 while it was still sending the frame (bad CRCs and lost
        # bytes in long frames, 2026-10-13 - it looked like a bad 8 Mbit/s line).
        if self.ser.timeout != timeout:
            self.ser.timeout = timeout
        self.ser.reset_input_buffer()
        self.ser.write(frame)
        hdr = self.ser.read(1)
        if not hdr:
            raise DebugPortError('no reply to command %02X' % cmd)
        if hdr[0] not in (0xA5, 0xB5):
            raise DebugPortError('bad reply header %02X to command %02X' % (hdr[0], cmd))
        n = 3 + (reply_len if hdr[0] == 0xA5 else 0) + 2
        rest = self.ser.read(n)
        if len(rest) != n:
            raise DebugPortError('short reply to command %02X (%d of %d bytes)' % (cmd, len(rest), n))
        reply = hdr + rest
        if crc16(reply) != 0:
            raise DebugPortError('reply CRC wrong (command %02X)' % cmd)
        if reply[1] != self.seq:
            raise DebugPortError('reply SEQ %02X, expected %02X' % (reply[1], self.seq))
        status = (reply[2] << 8) | reply[3]
        if status & 0x0002:
            raise DebugPortError('the FPGA saw a bad CRC in the request (command %02X)' % cmd)
        if status & 0x0004:
            raise DebugPortError('command %02X / %02X unknown to this FPGA build' % (cmd, attr))
        if status & 0x0008:
            raise DebugPortError('bad size (0 or over 16384, command %02X)' % cmd)
        if status & 0x0010:
            raise DebugPortError('address range refused (command %02X at $%08X: outside SRAM / flash read / DDR3, a '
                                 'block crossing an area, or SRAM / flash with the CPU not held)' % (cmd, addr))
        if status & 0x0080:
            raise DebugPortError('command %02X / %02X not allowed in this CPU state (%s)' % (cmd, attr, status_text(status)))
        return status, reply[4:4 + (reply_len if hdr[0] == 0xA5 else 0)]

    # ---- build 85: pause / step (stage 4), breakpoints (stage 5), monitor stop (stage 8) ----
    def pause(self):
        return self.transfer(0x30, 2, timeout=2.0)[0]

    def cont(self):
        return self.transfer(0x30, 3, timeout=2.0)[0]

    def step(self):
        return self.transfer(0x31, 0, timeout=2.0)[0]

    def bp_set(self, slot, addr, kinds='', mask=0):
        f = 0
        for k in kinds:
            f |= {'c': 0x02, 'r': 0x04, 'w': 0x08, 'n': 0x10}[k]
        if f & 0x0E:
            f |= 0x01 | (mask << 8)
        return self.transfer(0x20, slot, addr, f)[0]

    def report(self):
        w = [int.from_bytes(self.transfer(0x21, i, reply_len=4)[1], 'big') for i in (0, 1, 2)]
        slots = [(int.from_bytes(self.transfer(0x21, 4 + i, reply_len=4)[1], 'big'),
                  int.from_bytes(self.transfer(0x21, 8 + i, reply_len=4)[1], 'big')) for i in range(4)]
        return w, slots

    def nmi(self):
        return self.transfer(0x32, 0)[0]

    # ---- the MCP monitor stub (MCP 172+): mailbox in SRAM, Work/docs/DEBUG_MONITOR_STUB.md ----
    MB = 0x007FBE00

    def mb_read(self):
        b = self.read_mem(self.MB, 0x90)
        return [int.from_bytes(b[i:i + 4], 'big') for i in range(0, 0x90, 4)]

    def mb_cmd(self, cmd, addr=0, size=0, data=0, timeout=2.0):
        m = self.mb_read()
        if m[0] != 0x444D4F4E:
            raise DebugPortError('no monitor stub (MAGIC %08X): needs MCP 172+' % m[0])
        if m[2] != 1:
            raise DebugPortError('the CPU is not stopped in the monitor stub (use nmi first)')
        self.write_mem(self.MB + 0x18, addr.to_bytes(4, 'big') + size.to_bytes(4, 'big') + data.to_bytes(4, 'big'))
        self.write_mem(self.MB + 0x14, cmd.to_bytes(4, 'big'))          # CMD last: the stub starts on it
        t0 = time.time()
        while time.time() - t0 < timeout:
            m = self.mb_read()
            if m[5] == 0:
                return m
        raise DebugPortError('the monitor stub did not answer command %d' % cmd)

    def mb_wait_stop(self, count0, timeout=2.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            m = self.mb_read()
            if m[0] == 0x444D4F4E and m[2] == 1 and m[4] != count0:
                return m
            time.sleep(0.01)
        raise DebugPortError('the CPU did not stop in the monitor stub')

    # ---- stage 1 commands ----
    def revision(self):
        _, p = self.transfer(0x7E, reply_len=4)
        return {'block_rev': p[0], 'protocol': p[1], 'build': p[2]}

    def status(self):
        st, _ = self.transfer(0x7F, 0)
        return st

    def ext_status(self):
        _, p = self.transfer(0x7F, 1, reply_len=4)
        return int.from_bytes(p, 'big')

    def hold(self):
        return self.transfer(0x30, 0)[0]

    def release(self):
        return self.transfer(0x30, 1)[0]

    def system_reset(self):
        return self.transfer(0x3F, 0)[0]

    # ---- build 78: RxD line analyser ----
    def linemon_clear(self):
        return self.transfer(0x7F, 3)[0]

    def linemon(self):
        p = self.transfer(0x7F, 2, reply_len=4)[1]
        return {'min_low': p[0], 'min_high': p[1], 'short_low': p[2], 'short_high': p[3]}

    # ---- stage 2: memory ----
    CHUNK = 16384

    def read_mem(self, addr, count, label=None):
        """label: show a progress bar with this name (large blocks)."""
        out = bytearray()
        bar = Progress(label, count) if label else None
        while count > 0:
            n = min(count, self.CHUNK)
            out += self.transfer(0x00, 0, addr, n, reply_len=n, timeout=2.0)[1]
            addr += n
            count -= n
            if bar:
                bar.show(len(out))
        if bar:
            bar.finish()
        return bytes(out)

    def write_mem(self, addr, data, label=None):
        done = 0
        bar = Progress(label, len(data)) if label else None
        while done < len(data):
            n = min(len(data) - done, self.CHUNK)
            self.transfer(0x01, 0, addr + done, n, payload=data[done:done + n], timeout=2.0)
            done += n
            if bar:
                bar.show(done)
        if bar:
            bar.finish()

    # ---- stage 6: boot flash (CPU held). 4 MB at $FFC0_0000, two SST39VF1601 side by side: sector 8 KB, block 128 KB ----
    FLASH_BASE, FLASH_SIZE, SECTOR, BLOCK = 0xFFC00000, 0x400000, 0x2000, 0x20000

    def flash_id(self):
        """{manufacturer, manufacturer, device, device} low bytes of the two chips (SST39VF1601: BF BF 4B 4B)."""
        return self.transfer(0x10, 0, reply_len=4, timeout=2.0)[1]

    def flash_erase(self, addr, kind):
        """kind: 'sector' (8 KB), 'block' (128 KB) or 'chip'."""
        self.transfer(0x12, {'sector': 0, 'block': 1, 'chip': 2}[kind], addr, 0, timeout=3.0)

    def flash_program(self, addr, data, label=None):
        """Program an erased range, 16 KB per frame (the FPGA stages each frame in SRAM $7F_C000 first)."""
        if len(data) % 4 or addr % 4:
            raise DebugPortError('flash program: address and length must be multiples of 4')
        done = 0
        bar = Progress(label, len(data)) if label else None
        while done < len(data):
            n = min(len(data) - done, self.CHUNK)
            chunk = data[done:done + n]
            if chunk != b'\xff' * n:                        # erased already: nothing to program
                self.transfer(0x11, 0, addr + done, n, payload=chunk, timeout=3.0)
            done += n
            if bar:
                bar.show(done)
        if bar:
            bar.finish()

    def flash_write(self, addr, data, log=print):
        """Erase what the image covers (whole 128 KB blocks, 8 KB sectors at the edges), program, verify."""
        if addr < self.FLASH_BASE or addr + len(data) > self.FLASH_BASE + self.FLASH_SIZE:
            raise DebugPortError('flash range $%08X + %d is outside the flash' % (addr, len(data)))
        data = data + b'\xff' * (-len(data) % 4)
        start = addr & ~(self.SECTOR - 1)
        end = (addr + len(data) + self.SECTOR - 1) & ~(self.SECTOR - 1)
        t0 = time.time()
        a, ns, nb = start, 0, 0
        bar = Progress('erase', end - start)
        while a < end:
            if a % self.BLOCK == 0 and a + self.BLOCK <= end:
                self.flash_erase(a, 'block'); a += self.BLOCK; nb += 1
            else:
                self.flash_erase(a, 'sector'); a += self.SECTOR; ns += 1
            bar.show(a - start)
        bar.finish()
        log('erased $%08X-$%08X (%d block(s), %d sector(s)) in %.2f s' % (start, end - 1, nb, ns, time.time() - t0))
        t0 = time.time()
        self.flash_program(addr, data, label='program')
        dt = time.time() - t0
        log('programmed %d bytes in %.2f s (%.0f KB/s)' % (len(data), dt, len(data) / 1024 / max(dt, 1e-6)))
        back = self.read_mem(addr, len(data), label='verify')
        if back != data:
            first = next(i for i in range(len(data)) if back[i] != data[i])
            raise DebugPortError('flash verify failed at $%08X (read %02X, expected %02X)' % (addr + first, back[first], data[first]))
        log('verified')


def read_srec(path):
    """Data records of an S-record file, merged into contiguous blocks: [(address, bytes)]."""
    blocks = []
    for ln in open(path):
        ln = ln.strip()
        if ln[:2] not in ('S1', 'S2', 'S3'):
            continue
        al = {'S1': 4, 'S2': 6, 'S3': 8}[ln[:2]]
        n = int(ln[2:4], 16)
        a = int(ln[4:4 + al], 16)
        d = bytes.fromhex(ln[4 + al:2 + 2 * n])
        if blocks and blocks[-1][0] + len(blocks[-1][1]) == a:
            blocks[-1][1].extend(d)
        else:
            blocks.append((a, bytearray(d)))
    return [(a, bytes(d)) for a, d in blocks]


def hexdump(addr, data):
    for i in range(0, len(data), 16):
        row = data[i:i + 16]
        print('%08X: %-48s %s' % (addr + i, ' '.join('%02X' % b for b in row),
                                  ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)))


def print_regs(m):
    d, a = m[16:24], m[24:31]
    print('  reason %s, stop %d, PC $%08X, SR $%04X, frame $%04X' % ({1: 'NMI', 2: 'trace (step)'}.get(m[3], str(m[3])),
          m[4], m[34], m[33] & 0xFFFF, m[35] & 0xFFFF))
    print('  D0-D3 %08X %08X %08X %08X   D4-D7 %08X %08X %08X %08X' % tuple(d))
    print('  A0-A3 %08X %08X %08X %08X   A4-A6 %08X %08X %08X   A7(SSP) %08X  USP %08X' % (tuple(a) + (m[31], m[32])))


def status_text(st):
    names = [n for b, n in sorted(STATUS_BITS.items()) if st & (1 << b)]
    return '$%04X (%s)' % (st, ', '.join(names) if names else '-')


def main():
    ap = argparse.ArgumentParser(description='A2560Me debug protocol v2 host tool')
    ap.add_argument('--port', required=True, help='debug port (FT4232 channel B, e.g. COM18)')
    ap.add_argument('--baud', type=int, default=8_000_000)
    ap.add_argument('commands', nargs='*', choices=['rev', 'status', 'ext', 'hold', 'release', 'reset', 'selftest', 'linemon',
                                                     'flashid', 'pause', 'continue', 'step', 'report', 'nmi', 'regs',
                                                     'mstep', 'mcont'])
    ap.add_argument('--bp', action='append', default=[], metavar='SLOT:ADDR[:KINDS[:MASK]]',
                    help='set a breakpoint (build 85+): KINDS from c r w n, MASK = ignored low address bits')
    ap.add_argument('--bp-clear', action='append', type=int, default=[], metavar='SLOT', help='clear a breakpoint slot')
    ap.add_argument('--peek', metavar='ADDR[:SIZE]', help='monitor stub: read 1 / 2 / 4 bytes (default 4) at a hex address')
    ap.add_argument('--poke', metavar='ADDR:VALUE[:SIZE]', help='monitor stub: write 1 / 2 / 4 bytes (hex) at a hex address')
    ap.add_argument('--flash', metavar='FILE', help='write a binary image into the boot flash (--block N or --address), '
                    'erase only what it covers, verify, then system reset (build 82+)')
    ap.add_argument('--block', type=int, help='--flash: block number in the --layout')
    ap.add_argument('--layout', choices=['512k', '1m', '2m', '4m'], default='512k',
                    help='--flash --block: block size (default 512k: block N at $FFC0_0000 + N x 512 KB)')
    ap.add_argument('--no-reset', action='store_true', help='--flash: leave the CPU held instead of resetting')
    ap.add_argument('--dump', type=lambda x: int(x, 16), metavar='ADDR', help='read memory (hex address)')
    ap.add_argument('--count', type=lambda x: int(x, 0), default=256, help='bytes to read with --dump')
    ap.add_argument('--out', metavar='FILE', help='--dump: write the bytes to FILE instead of a listing')
    ap.add_argument('--load', metavar='FILE', help='write a binary file to --address')
    ap.add_argument('--address', type=lambda x: int(x, 16), metavar='ADDR', help='hex address for --load / --run')
    ap.add_argument('--srec', metavar='FILE', help='write an S-record file')
    ap.add_argument('--run', metavar='FILE', help='hold, load (S-record or binary at --address), verify, release')
    ap.add_argument('--no-verify', action='store_true', help='--run / --load / --srec: skip the read-back')
    ap.add_argument('--reset-first', action='store_true',
                    help='--run: system reset first (clean peripherals, like a power-up), then hold, load, release')
    a = ap.parse_args()
    if not (a.commands or a.dump is not None or a.load or a.srec or a.run or a.flash or a.bp or a.bp_clear or a.peek or a.poke):
        ap.error('nothing to do')
    if a.commands == ['selftest']:
        ok = crc16(b'123456789') == 0x29B1
        print('CRC-16/CCITT-FALSE check value:', 'OK' if ok else 'WRONG')
        return 0 if ok else 1
    try:
        d = DebugPortV2(a.port, a.baud)
    except Exception as e:
        print('ERROR:', e)
        return 1
    try:
        for spec in a.bp:
            f = spec.split(':')
            slot, addr = int(f[0]), int(f[1], 16)
            kinds = f[2].lower() if len(f) > 2 else 'c'
            mask = int(f[3], 0) if len(f) > 3 else 0
            d.bp_set(slot, addr, kinds, mask)
            print('breakpoint %d: $%08X %s, %d low bits ignored' % (slot, addr, kinds, mask))
        for slot in a.bp_clear:
            d.bp_set(slot, 0)
            print('breakpoint %d cleared' % slot)
        for c in a.commands:
            if c == 'pause':
                st = d.pause()
                print('pause:', status_text(st), '' if st & 0x0200 else '(not paused yet: the CPU keeps the bus)')
            elif c == 'continue':
                print('continue:', status_text(d.cont()))
            elif c == 'step':
                print('step:', status_text(d.step()))
            elif c == 'report':
                w, slots = d.report()
                st = w[0]
                print('debug report: %s, hit %s' % ('paused' if st & 8 else 'held' if st & 4 else 'running',
                      ('slot %d at $%08X, %s, TT %d, TM %d' % (st & 3, w[1], 'read' if (st >> 21) & 1 else 'write',
                       (st >> 19) & 3, (st >> 16) & 7)) if st & 0x80 else 'none'))
                print('  CPU bus cycles seen: %d' % w[2])
                for i, (ad, fl) in enumerate(slots):
                    kinds = ''.join(k for k, bit in (('c', 2), ('r', 4), ('w', 8), ('n', 16)) if fl & bit)
                    print('  slot %d: %s $%08X %s mask %d' % (i, 'on ' if fl & 1 else 'off', ad, kinds or '-', (fl >> 8) & 31))
            elif c == 'nmi':
                c0 = d.mb_read()[4]
                d.nmi()
                m = d.mb_wait_stop(c0)
                print('stopped in the monitor stub:')
                print_regs(m)
            elif c == 'regs':
                m = d.mb_read()
                if m[0] != 0x444D4F4E or m[2] != 1:
                    raise DebugPortError('the CPU is not stopped in the monitor stub')
                print_regs(m)
            elif c == 'mstep':
                c0 = d.mb_read()[4]
                d.mb_cmd(2)
                m = d.mb_wait_stop(c0)
                print_regs(m)
            elif c == 'mcont':
                d.mb_cmd(1)
                d.cont()                                    # re-arm the breakpoints (BP_HIT) after a stop
                print('continued')
            elif c == 'rev':
                r = d.revision()
                print('revision: debug block $%02X, protocol %d, FPGA build %d' % (r['block_rev'], r['protocol'], r['build']))
            elif c == 'status':
                print('status:', status_text(d.status()))
            elif c == 'ext':
                e = d.ext_status()
                print('extended status $%08X: CPU %s, debug bus %s, NMI %s, CRC errors %d, time-outs %d, layout %d' % (
                    e, 'held' if e & 1 else 'paused' if e & 4 else 'running', 'owned' if e & 2 else 'free',
                    'pending' if e & 8 else '-', (e >> 8) & 0xFF, (e >> 16) & 0xFF, e >> 24))
            elif c == 'hold':
                print('hold:', status_text(d.hold()))
            elif c == 'release':
                print('release:', status_text(d.release()))
            elif c == 'reset':
                print('system reset:', status_text(d.system_reset()))
            elif c == 'flashid':
                i = d.flash_id()
                print('flash ID: manufacturer %02X %02X, device %02X %02X%s' % (i[0], i[1], i[2], i[3],
                      '  (SST39VF1601 pair)' if bytes(i) == b'\xbf\xbf\x4b\x4b' else ''))
            elif c == 'linemon':
                # clear, send 4 KB of 0x55 (single-bit pulses of both levels) as a refused write, read the statistics
                d.linemon_clear()
                try:
                    d.transfer(0x01, 0, 0x00800000, 4096, payload=b'\x55' * 4096)
                except DebugPortError:
                    pass                                    # refused (RANGE) or damaged: only the line matters
                m = d.linemon()
                print('RxD line (5 ns clocks, 8 Mbit/s bit = 25): shortest low %d (%d ns), shortest high %d (%d ns), '
                      'short (<95 ns) low pulses %d, high pulses %d' % (m['min_low'], 5 * m['min_low'], m['min_high'],
                                                                     5 * m['min_high'], m['short_low'], m['short_high']))
        if a.run or a.load or a.srec:
            path = a.run or a.load or a.srec
            if a.srec or (a.run and path.lower().endswith(('.s68', '.srec', '.s19', '.s28', '.s37', '.mot'))):
                blocks = read_srec(path)
            else:
                if a.address is None:
                    raise DebugPortError('a binary file needs --address')
                blocks = [(a.address, open(path, 'rb').read())]
            total = sum(len(b) for _, b in blocks)
            if a.run:
                if a.reset_first:
                    d.system_reset()
                    d.close()
                    time.sleep(3.0)                          # about 1.2 s of reset, then the boot copy
                    d = DebugPortV2(a.port, a.baud)
                d.hold()
            t0 = time.time()
            for addr, data in blocks:
                d.write_mem(addr, data, label='load' if len(data) > d.CHUNK else None)
            dt = time.time() - t0
            print('loaded %d bytes in %d block(s), %.2f s (%.0f KB/s)' % (total, len(blocks), dt, total / 1024 / max(dt, 1e-6)))
            if not a.no_verify:
                bad = 0
                for addr, data in blocks:
                    back = d.read_mem(addr, len(data), label='verify' if len(data) > d.CHUNK else None)
                    if back != data:
                        bad += 1
                        first = next(i for i in range(len(data)) if back[i] != data[i])
                        print('VERIFY FAILED at $%08X' % (addr + first))
                if bad:
                    raise DebugPortError('%d block(s) differ after loading' % bad)
                print('verified')
            if a.run:
                d.release()
                print('CPU released')
        if a.flash:
            img = open(a.flash, 'rb').read()
            if a.block is not None:
                size = {'512k': 0x80000, '1m': 0x100000, '2m': 0x200000, '4m': 0x400000}[a.layout]
                if a.block * size >= DebugPortV2.FLASH_SIZE:
                    raise DebugPortError('block %d does not exist in the %s layout' % (a.block, a.layout))
                if len(img) > size:
                    raise DebugPortError('%s is %d bytes, more than one %s block' % (a.flash, len(img), a.layout))
                addr = DebugPortV2.FLASH_BASE + a.block * size
            elif a.address is not None:
                addr = a.address
            else:
                raise DebugPortError('--flash needs --block N (with --layout) or --address')
            print('flashing %s (%d bytes) at $%08X' % (a.flash, len(img), addr))
            # the flash must answer with the SST39VF1601 ID before anything is erased (just after a system reset the
            # boot copy owns the flash pins and the debug port reads $FF): retry for 5 s, then refuse
            r = d.revision()
            if r['block_rev'] < 0x13:
                raise DebugPortError('the FPGA (build %d, debug block $%02X) has no flash commands: load build 82 or '
                                     'later. Nothing written.' % (r['build'], r['block_rev']))
            t0, i, last = time.time(), b'', ''
            while time.time() - t0 < 5.0:
                try:
                    d.hold()
                    i = bytes(d.flash_id())
                    if i == b'\xbf\xbf\x4b\x4b':
                        break
                except DebugPortError as e:
                    last = str(e)
                time.sleep(0.25)
            if i != b'\xbf\xbf\x4b\x4b':
                raise DebugPortError('flash ID "%s", not the SST39VF1601 pair%s: nothing written'
                                     % (i.hex(), (' (' + last + ')') if last else ''))
            d.flash_write(addr, img)
            if a.no_reset:
                print('CPU left held')
            else:
                d.system_reset()
                print('system reset: the board boots from the flash')
        if a.peek:
            f = a.peek.split(':')
            m = d.mb_cmd(3, int(f[0], 16), int(f[1]) if len(f) > 1 else 4)
            print('peek $%08X: %s' % (int(f[0], 16), ('$%X' % m[8]) if m[9] == 0 else ('error $%08X' % m[9])))
        if a.poke:
            f = a.poke.split(':')
            m = d.mb_cmd(4, int(f[0], 16), int(f[2]) if len(f) > 2 else 4, int(f[1], 16))
            print('poke $%08X: %s' % (int(f[0], 16), 'OK' if m[9] == 0 else ('error $%08X' % m[9])))
        if a.dump is not None:
            data = d.read_mem(a.dump, a.count, label='read' if a.count > d.CHUNK else None)
            if a.out:
                open(a.out, 'wb').write(data)
                print('%d bytes written to %s' % (len(data), a.out))
            else:
                hexdump(a.dump, data)
    except DebugPortError as e:
        print('ERROR:', e)
        return 1
    finally:
        d.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
