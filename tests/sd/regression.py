#!/usr/bin/env python3
"""Run the actual sd.c with a scripted SPI card; no board or card writes."""
# Distributed under GPL version 2 or later; see doc/license.txt.
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, default=root / 'bios/sd.c')
args = parser.parse_args()
source = re.sub(r'^#include .*$', '', args.source.read_text(), flags=re.M)
spi = re.sub(r'^#include .*$', '', (root / 'bios/spi.h').read_text(), flags=re.M)
prefix = r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef int16_t WORD;
typedef uint32_t ULONG;
typedef int32_t LONG;
#define MACHINE_A2560M 1
#define CONF_WITH_SDMMC 1
#define KDEBUG(x) ((void)0)
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define CLOCKS_PER_SEC 200
#define SECTOR_SIZE 512
#define LOBYTE(x) ((UBYTE)(x))
#define EUNDEV -15
#define EDRVNR -2
#define E_CHNG -14
#define EREADF -11
#define EWRITF -10
#define ERR -1
#define RW_RW 1
#define RW_NOMEDIACH 2
#define GET_DISKINFO 20
#define GET_DISKNAME 21
#define GET_MEDIACHANGE 30
#define MEDIANOCHANGE 0
#define MEDIACHANGE 2
static ULONG hz_200, loopcount_1_msec;
static void delay_loop(ULONG n) { (void)n; hz_200++; }
'''
tests = r'''
static UBYTE packet[6], reply[5];
static unsigned sent, reply_pos, reply_len, counts[64], selects, deselects;
static int block_addressing, reject_cmd16, stream;
static void noop(void) {}
static void select_card(void) { selects++; }
static void deselect_card(void) { deselects++; }
static void send_byte(UBYTE b)
{
    unsigned cmd;
    if (!sent && b == 0xff) return;
    packet[sent++] = b;
    if (sent != 6) return;
    sent = 0;
    cmd = packet[0] & 63;
    counts[cmd]++;
    memset(reply, 0, sizeof(reply));
    reply_pos = 0;
    reply_len = 1;
    if (cmd == CMD0) reply[0] = 1;
    if (cmd == CMD8) {
        reply[0] = 1; reply[3] = 1; reply[4] = 0xaa; reply_len = 5;
    }
    if (cmd == CMD58) {
        reply[1] = block_addressing ? 0x40 : 0; reply_len = 5;
    }
    if (cmd == CMD16 && reject_cmd16) reply[0] = 4;
    if (cmd == CMD12) {
        reply[0] = 0xff; reply[1] = 0; reply_len = 2; stream = 0;
    }
}
static UBYTE recv_byte(void)
{
    hz_200++;
    if (reply_pos < reply_len) return reply[reply_pos++];
    return stream ? 0x55 : 0xff;
}
const SPI_DRIVER spi_a2560m_sd0 = {
    noop, noop, noop, noop, select_card, deselect_card,
    send_byte, recv_byte, noop, noop, 0
};
const SPI_DRIVER spi_a2560m_sd1 = {
    noop, noop, noop, noop, select_card, deselect_card,
    send_byte, recv_byte, noop, noop, 0
};
static void reset_mock(void)
{
    hz_200 = 0; sent = reply_len = reply_pos = selects = deselects = 0;
    stream = 0;
    memset(counts, 0, sizeof(counts));
}
int main(void)
{
    struct cardinfo card = {0};
    UBYTE csd[16] = {0x40}, resp[5];
    unsigned i;
    card.spi_driver = (SPI_DRIVER *)&spi_a2560m_sd0;
    block_addressing = 1; reject_cmd16 = 1;
    reset_mock();
    assert(sd_check(&card) == 0);
    assert(card.features & BLOCK_ADDRESSING);
    assert(counts[CMD16] == 0);
    block_addressing = 0; reject_cmd16 = 0;
    reset_mock();
    assert(sd_check(&card) == 0);
    assert(counts[CMD16] == 1);
    reject_cmd16 = 1;
    reset_mock();
    assert(sd_check(&card) == EDRVNR);
    card.type = CARDTYPE_SD;
    assert(sd_calc_capacity(csd, &card) == 1024);
    csd[9] = 1;
    assert(sd_calc_capacity(csd, &card) == 2048);
    reset_mock();
    stream = 1; /* No idle byte occurs until CMD12 stops the stream. */
    assert(sd_command(CMD12, 0, 0, R1B, resp, card.spi_driver) == 0);
    assert(counts[CMD12] == 1 && selects == 0 && deselects == 0);
    reset_mock();
    assert(sd_command(CMD17, 0, 0, R1, resp, card.spi_driver) == 0);
    assert(selects == 1 && deselects == 1);
    for (i = MAX_SD_CARDS; i < 16; i++) {
        assert(sd_ioctl(i, GET_DISKINFO, NULL) == EUNDEV);
        assert(sd_rw(0, 0, 1, NULL, i) == EUNDEV);
    }
    assert(sd_rw(0, 0, 1, NULL, -1) == EUNDEV);
    assert(sd_ioctl(65535, GET_DISKINFO, NULL) == EUNDEV);
    puts("PASS: SDHC/SDSC init, CMD16 failure, capacity, CMD12 streaming, CS framing, device bounds");
}
'''
with tempfile.TemporaryDirectory(prefix='sd-regression-') as d:
    c = Path(d) / 'test.c'
    exe = Path(d) / 'test'
    c.write_text(prefix + spi + source + tests)
    subprocess.run(['cc', '-std=c99', '-g', '-fsanitize=address,undefined',
                    str(c), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
