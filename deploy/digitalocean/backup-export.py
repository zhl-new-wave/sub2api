#!/usr/bin/env python3
"""Forced SSH command: export only the latest encrypted backup and metadata."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

root = Path('/opt/sub2api/backups').resolve()
metadata = json.loads((root / 'last-success.json').read_text())
path = root / metadata['file']
if path.is_symlink() or path.resolve().parent != root or not path.is_file():
    raise SystemExit('Invalid encrypted backup path')
digest = hashlib.sha256()
with path.open('rb') as stream:
    for block in iter(lambda: stream.read(1024 * 1024), b''): digest.update(block)
if digest.hexdigest() != metadata['sha256']:
    raise SystemExit('Backup checksum mismatch')
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|') as archive:
    archive.add(path, arcname='bundle.age')
    payload = (json.dumps(metadata, indent=2) + '\n').encode()
    member = tarfile.TarInfo('metadata.json')
    member.size = len(payload)
    member.mode = 0o600
    archive.addfile(member, io.BytesIO(payload))
