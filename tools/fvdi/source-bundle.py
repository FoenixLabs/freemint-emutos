#!/usr/bin/env python3
"""Bundle the pinned fVDI source and our driver overlay; GPL-2.0-or-later."""
from pathlib import Path
import gzip
import io
import subprocess
import tarfile
import shutil

root=Path(__file__).resolve().parents[2]
repo=root.parent/'fvdi'
out=root/'drive_d/MINT/SOURCE'
out.mkdir(parents=True,exist_ok=True)
archive=subprocess.check_output(['git','-C',str(repo),'archive','--prefix=fvdi/','HEAD'])
stream=io.BytesIO(archive)
with tarfile.open(fileobj=stream,mode='a') as tar:
    for path in sorted((root/'tools/fvdi/a2560me').iterdir()):
        if path.is_file():
            tar.add(path,arcname='fvdi/fvdi/drivers/a2560me/'+path.name)
    for path in sorted((root/'tools/fvdi/probe').iterdir()):
        if path.is_file():
            tar.add(path,arcname='fvdi/a2560me-probe/'+path.name)
(out/'FVDISRC.TGZ').write_bytes(gzip.compress(stream.getvalue(),mtime=0))
for source,target in [('README.TXT','FVDI.TXT'),('rebuild.sh','FVBUILD.SH')]:
    shutil.copy2(root/'tools/fvdi'/source,out/target)
