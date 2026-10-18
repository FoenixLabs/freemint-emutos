#!/usr/bin/env python3
"""Exercise bios/ide.c with a host ATA model, without accessing a real disk.

Only MMIO reads/writes, m68k transfer assembly, and platform dependencies are
substituted. Driver detection, command sequencing, and request handling run
from the production source. IDENTIFY reads model the byte reversal performed by GAVIN.
Distributed under GPL version 2 or later; see doc/license.txt.
"""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = re.sub(r'^#include .*$', '', (root / 'bios/ide.c').read_text(), flags=re.M)
source = re.sub(r'(#\s*define IDE_READ_(?:ALT_)?STATUS\(i\))\s+i->command',
                r'\1 mock_status(i)', source)
source = source.replace('i->command = a;', 'mock_command(i,a);')
source = source.replace('interface->command = IDE_CMD_NOP;',
                        'mock_command(interface,IDE_CMD_NOP);')
source = re.sub(r'^#define ide_get_and_incr.*$',
                '#define ide_get_and_incr(src,dst) (*(dst)++ = mock_read())', source, flags=re.M)
source = re.sub(r'^#define ide_put_and_incr.*$',
                '#define ide_put_and_incr(src,dst) mock_write(*(src)++)', source, flags=re.M)
source = source.replace('temp = interface->data;', 'temp = mock_read();')
source = source.replace('temp = *(UWORD_ALIAS *)&interface->data;', 'temp = mock_read();')
source = source.replace('*p2++ = *(UWORD_ALIAS *)&interface->data;', '*p2++ = mock_read();')
source = source.replace('*(UWORD_ALIAS *)&interface->data = temp;', 'mock_write(temp);')
source = source.replace('*(UWORD_ALIAS *)&interface->data = *p2++;', 'mock_write(*p2++);')
source = source.replace('interface->data = temp;', 'mock_write(temp);')
source = source.replace('((ULONG)interface)', '((uintptr_t)interface)')
header = (root / 'foenix/a2560.h').read_text()
layout = header[header.index('struct IDE'):header.index('#define ide_interface')]
prefix = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
typedef uint8_t UBYTE;
typedef uint16_t UWORD;
typedef int16_t WORD;
typedef uint32_t ULONG;
typedef int32_t LONG;
typedef int BOOL;
typedef UWORD UWORD_ALIAS;
#define TRUE 1
#define FALSE 0
#define MACHINE_A2560M 1
#define CONF_WITH_IDE 1
#define KDEBUG(x) ((void)0)
#define KINFO(x) ((void)0)
#define MAYBE_UNUSED(x) ((void)(x))
#define CLOCKS_PER_SEC 200UL
#define SECTOR_SIZE 512
#define DEVICES_PER_BUS 8
#define DSKBUF_SECS 2
#define EUNDEV -15
#define EGENRL -12
#define ESECNF -8
#define EREADF -11
#define EWRITF -10
#define ERR -1
#define E_OK 0
#define RW_RW 1
#define GET_DISKINFO 20
#define GET_DISKNAME 21
#define GET_MEDIACHANGE 30
#define MEDIANOCHANGE 0
#define LOBYTE(x) ((UBYTE)(x))
#define HIBYTE(x) ((UBYTE)((x)>>8))
#define MAKE_UWORD(a,b) (((UWORD)(a)<<8)|(UBYTE)(b))
#define MAKE_ULONG(a,b) (((ULONG)(a)<<16)|(UWORD)(b))
#define IS_ODD_POINTER(p) ((uintptr_t)(p)&1)
#define divu(a,b) ((a)/(b))
#define swpw(a) ((a) = ((a)>>8)|((a)<<8))
static ULONG hz_200, loopcount_1_msec = 50000;
static UWORD mcpu = 60;
static UBYTE diskbuf[1024], *dskbufp = diskbuf;
static void delay_loop(ULONG n) { (void)n; }
'''
transport = r'''
static struct IDE regs;
#define ide_interface (&regs)
static UBYTE mock_status(volatile struct IDE *r);
static void mock_command(volatile struct IDE *r, UBYTE cmd);
static UWORD mock_read(void);
static void mock_write(UWORD value);
'''
tests = r'''
static struct IDENTIFY identity;
static UWORD disk[3][256];
static UWORD *transfer;
static unsigned words, polls, commands[256], last_head, lba_count;
static ULONG lbas[8];
static UBYTE status;
static int absent, fail_identify, fail_io, stuck, large, identify_transfer;
static UBYTE mock_status(volatile struct IDE *r)
{
    (void)r;
    hz_200++;
    if (absent) return 0;
    if (stuck) return IDE_STATUS_BSY;
    if (polls) { polls--; return IDE_STATUS_BSY; }
    return status;
}
static void mock_command(volatile struct IDE *r, UBYTE cmd)
{
    ULONG sector;
    commands[cmd]++;
    polls = 2;
    words = 0;
    identify_transfer = 0;
    status = IDE_STATUS_DRDY;
    last_head = r->head;
    if (cmd == IDE_CMD_NOP) return;
    assert((last_head & 0xa0) == 0xa0);
    assert(!(last_head & 0x10));
    if (cmd == IDE_CMD_IDENTIFY_DEVICE) {
        if (fail_identify) { status |= IDE_STATUS_ERR; return; }
        transfer = (UWORD *)&identity;
        identify_transfer = 1;
    } else if (cmd == IDE_CMD_READ_SECTOR || cmd == IDE_CMD_WRITE_SECTOR
            || cmd == IDE_CMD_READ_SECTOR_EX || cmd == IDE_CMD_WRITE_SECTOR_EX) {
        assert(r->sector_count == 1);
        assert(last_head & 0x40);
        sector = ((ULONG)(r->head & 15)<<24) | ((ULONG)r->cylinder_high<<16)
               | ((ULONG)r->cylinder_low<<8) | r->sector_number;
        if (!large) assert(sector < 3);
        if (lba_count < 8) lbas[lba_count++] = sector;
        if (fail_io) { status |= IDE_STATUS_ERR; return; }
        transfer = disk[large ? 0 : sector];
    } else {
        assert(!"unexpected command (MULTIPLE/CHS must not be enabled)");
    }
    status |= IDE_STATUS_DRQ;
}
static UWORD mock_read(void)
{
    UWORD value;
    assert((status & IDE_STATUS_DRQ) && words < 256);
    value = transfer[words++];
    /* GAVIN presents IDENTIFY numeric words byte-reversed to the CPU. */
    if (identify_transfer) swpw(value);
    if (words == 256) status = IDE_STATUS_DRDY;
    return value;
}
static void mock_write(UWORD value)
{
    assert((status & IDE_STATUS_DRQ) && words < 256);
    transfer[words++] = value;
    if (words == 256) { status = IDE_STATUS_DRDY; polls = 2; }
}
static void boot(int missing, int bad_identify, int busy, int no_lba)
{
    memset(&regs,0,sizeof(regs));
    memset(&identity,0,sizeof(identity));
    memset(commands,0,sizeof(commands));
    identity.capabilities = no_lba ? 0 : LBA_SUPPORTED;
    identity.numsecs_lba28[0] = 12345;
    identity.multiple_io_info = 0x8010;
    memset(identity.model_number,' ',sizeof(identity.model_number));
    memcpy(identity.model_number,"MSATA TEST SSD",14);
    absent = missing; fail_identify = bad_identify; stuck = busy;
    fail_io = large = 0; hz_200 = polls = words = lba_count = 0;
    status = IDE_STATUS_DRDY;
    assert(detect_ide());
    ide_init();
    assert(hz_200 < 2000); /* Missing/busy devices must not hang boot. */
}
int main(void)
{
    UWORD buffer[768], expected[768];
    ULONG info[2];
    char name[64];
    unsigned i;
    assert(sizeof(struct IDE) == 16);
    assert(offsetof(struct IDE,data) == 0);
    assert(offsetof(struct IDE,features) == 2);
    assert(offsetof(struct IDE,sector_count) == 4);
    assert(offsetof(struct IDE,sector_number) == 6);
    assert(offsetof(struct IDE,cylinder_low) == 8);
    assert(offsetof(struct IDE,cylinder_high) == 10);
    assert(offsetof(struct IDE,head) == 12);
    assert(offsetof(struct IDE,command) == 14);
    boot(1,0,0,0);
    assert(ide_device_type(0) == DEVTYPE_NONE);
    boot(0,1,0,0);
    assert(ide_device_type(0) == DEVTYPE_NONE);
    boot(0,0,1,0);
    assert(ide_device_type(0) == DEVTYPE_NONE);
    boot(0,0,0,1);
    assert(ide_device_type(0) == DEVTYPE_NONE);
    boot(0,0,0,0);
    assert(ide_device_type(0) == DEVTYPE_ATA);
    for (i = 1; i < 8; i++) assert(ide_device_type(i) == DEVTYPE_NONE);
    assert(ide_device_type(-1) == DEVTYPE_NONE);
    assert(!(ifinfo[0].dev[0].options & CHS_MODE));
    assert(!(ifinfo[0].dev[0].options & MULTIPLE_MODE_ACTIVE));
    assert(ide_ioctl(0,GET_DISKINFO,info) == 0);
    assert(info[0] == 12345 && info[1] == 512);
    assert(ide_ioctl(0,GET_DISKNAME,name) == 0);
    assert(strcmp(name,"MSATA TEST SSD") == 0);
    for (i = 0; i < 768; i++) expected[i] = buffer[i] = (i*257) ^ 0x1234;
    assert(ide_rw(1,0,3,(UBYTE *)buffer,0,FALSE) == 0);
    assert(commands[IDE_CMD_WRITE_SECTOR] == 3);
    assert(lbas[0] == 0 && lbas[1] == 1 && lbas[2] == 2);
    memset(buffer,0,sizeof(buffer));
    assert(ide_rw(0,0,3,(UBYTE *)buffer,0,FALSE) == 0);
    assert(memcmp(buffer,expected,sizeof(buffer)) == 0);
    assert(ide_rw(1,0,3,(UBYTE *)expected,0,TRUE) == 0);
    assert(disk[0][0] == 0x3412);
    assert(ide_rw(0,0,3,(UBYTE *)buffer,0,TRUE) == 0);
    assert(memcmp(buffer,expected,sizeof(buffer)) == 0);
    fail_io = 1;
    assert(ide_rw(0,0,1,(UBYTE *)buffer,0,FALSE) == EREADF);
    assert(ide_rw(1,0,1,(UBYTE *)buffer,0,FALSE) == EWRITF);
    fail_io = 0;
    assert(ide_rw(1,0x10000000,1,(UBYTE *)buffer,0,FALSE) == ESECNF);
    assert(ide_rw(1,0x0fffffff,2,(UBYTE *)buffer,0,FALSE) == ESECNF);
    large = 1;
    set_lba48_mode(0,IDE_CAPABILITY_LBA48);
    assert(ide_rw(1,0xffffffff,2,(UBYTE *)buffer,0,FALSE) == ESECNF);
    assert(ide_rw(0,0x10000000,1,(UBYTE *)buffer,0,FALSE) == 0);
    assert(commands[IDE_CMD_READ_SECTOR_EX] == 1);
    puts("PASS: register map, absent/busy/failed IDENTIFY, primary-only detection, GAVIN IDENTIFY byte order, non-LBA rejection, capacity/name, PIO read/write, byte swap, errors, LBA28 bounds, LBA48 selection");
}
'''
with tempfile.TemporaryDirectory(prefix='ide-regression-') as d:
    c = Path(d) / 'test.c'
    exe = Path(d) / 'test'
    c.write_text(prefix + layout + transport + source + tests)
    subprocess.run(['cc', '-std=c99', '-g', '-fsanitize=address,undefined',
                    str(c), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
