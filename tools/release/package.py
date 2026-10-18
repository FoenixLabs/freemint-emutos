#!/usr/bin/env python3
"""Package validated ROMs, drive trees and complete working sources; GPL-2.0+."""
from pathlib import Path
import argparse, gzip, hashlib, io, re, shutil, struct, subprocess, tarfile, zipfile

root=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--name',default='a2560me-freemint-fvdi-20261017')
args=parser.parse_args()
if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]+',args.name):
    parser.error('name must be a simple directory name')
release=root/'releases'/args.name
archive=release.with_suffix('.zip')
if release.exists() or archive.exists():
    parser.error('release already exists; choose a new --name')
for name,pc in [('emutos-a2560m.rom',0xffd00008),
                ('emutos-a2560m-sram.rom',0xffd00008),
                ('emutos-a2560m-ram.rom',0x00100008)]:
    data=(root/name).read_bytes()
    assert len(data)==524288 and struct.unpack_from('>I',data,4)[0]==pc,name
assert (root/'drive_d/MINT/MINT.CNF').read_bytes()==(root/'drive_d/MINT/FVDI.CNF').read_bytes()
assert (root/'localconf.h').read_bytes()==(root/'tools/fvdi/firmware-localconf.h').read_bytes()
subprocess.run(['python3',str(root/'tools/freemint/manifest.py')],check=True)
subprocess.run(['python3',str(root/'tools/fvdi/verify.py')],check=True)
release.mkdir(parents=True)
for folder in ('drive_c','drive_d'):
    shutil.copytree(root/folder,release/folder)
for name in ('emutos-a2560m.rom','emutos-a2560m-sram.rom','emutos-a2560m-ram.rom','upload-to-flash.sh'):
    shutil.copy2(root/name,release/name)
(release/'tools').mkdir()
shutil.copy2(root/'tools/a2560me_dbg.py',release/'tools/a2560me_dbg.py')
for name in ('README.TXT','VALIDATION.TXT'):
    shutil.copy2(root/'tools/release'/name,release/name)
shutil.copy2(root/'doc/license.txt',release/'COPYING')
(release/'source').mkdir()
# Git archive HEAD would lose staged/unstaged board changes and new drivers.
# Snapshot all source from the working tree, excluding personal/lab/output data.
names=set(subprocess.check_output(['git','-C',str(root),'ls-files','-z','-c','-o','--exclude-standard']).decode().split('\0'))
names.discard('')
names.add('localconf.h')
excluded={'drive_c','drive_d','logs','releases','.git','.vscode','.idea'}
stream=io.BytesIO(); count=0
with tarfile.open(fileobj=stream,mode='w') as tar:
    for name in sorted(names):
        path=root/name; parts=Path(name).parts
        if parts[0] in excluded or path.name=='AGENTS.md' or path.suffix in ('.log','.o','.a'):
            continue
        if not path.is_file():
            continue
        if path.is_symlink():
            raise RuntimeError('unexpected source symlink: '+name)
        info=tarfile.TarInfo('emutos/'+name)
        data=path.read_bytes(); info.size=len(data)
        info.mode=0o755 if path.stat().st_mode&0o111 else 0o644
        info.mtime=1792195200; info.uid=info.gid=0
        tar.addfile(info,io.BytesIO(data)); count+=1
(release/'source/EMUTOSSRC.TGZ').write_bytes(gzip.compress(stream.getvalue(),mtime=0))
revision=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
(release/'BUILD.TXT').write_text('A2560Me release 2026-10-17\n'
    +'EmuTOS base revision: '+revision+'\n'
    +'Source is the complete modified working tree, not an unmodified commit.\n'
    +f'EmuTOS snapshot: {count} source/build/license files.\n'
    +'Profile: tools/fvdi/firmware-localconf.h (also included as localconf.h).\n'
    +'Component revisions and firmware/kernel identities: drive_c/BUILD.TXT.\n'
    +'ROM flash/readback and colour boot validated on physical target.\n')
lines=[]
for path in sorted(release.rglob('*')):
    if path.is_file():
        assert not path.is_symlink()
        lines.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.relative_to(release).as_posix())
(release/'SHA256.TXT').write_text('\n'.join(lines)+'\n')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path in sorted(release.rglob('*')):
        if path.is_file():
            info=zipfile.ZipInfo(args.name+'/'+path.relative_to(release).as_posix(),(2026,10,17,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(path.stat().st_mode & 0xffff)<<16
            z.writestr(info,path.read_bytes())
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n')
# Verify archive content and source exclusions independently after writing.
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for line in (release/'SHA256.TXT').read_text().splitlines():
        expected,name=line.split('  ',1)
        assert hashlib.sha256(z.read(args.name+'/'+name)).hexdigest()==expected,name
with tarfile.open(release/'source/EMUTOSSRC.TGZ','r:gz') as tar:
    members=tar.getnames()
    assert 'emutos/localconf.h' in members
    assert 'emutos/tools/fvdi/a2560me/dma.h' in members
    assert 'emutos/bios/memory2.c' in members
    assert not any('/logs/' in n or n.endswith('pikvm.log') or '/.git/' in n for n in members)
print(archive)
print(digest)
