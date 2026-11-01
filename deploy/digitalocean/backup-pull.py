#!/usr/bin/env python3
"""Receive the latest encrypted backup using a restricted SSH identity."""

import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile


def receive_backup(root, command, keep=35, max_age_hours=36):
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    folder = root / 'backups'
    folder.mkdir(mode=0o700, exist_ok=True)
    with (root / '.backup-pull.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(prefix='.incoming-', dir=root) as temp:
            work = Path(temp)
            with (work / 'incoming.tar').open('xb') as stream:
                subprocess.run(command, stdout=stream, check=True, timeout=300)
            with tarfile.open(work / 'incoming.tar') as archive:
                members = archive.getmembers()
                if (len(members) != 2 or
                        {m.name for m in members} != {'bundle.age', 'metadata.json'} or
                        any(not m.isfile() for m in members)):
                    raise ValueError('Unexpected backup export content')
                for member in members:
                    with (work / member.name).open('xb') as stream:
                        source = archive.extractfile(member)
                        while block := source.read(1024 * 1024):
                            stream.write(block)
            metadata = json.loads((work / 'metadata.json').read_text())
            created = datetime.datetime.strptime(
                metadata['created_utc'], '%Y%m%dT%H%M%SZ'
            ).replace(tzinfo=datetime.timezone.utc)
            age = datetime.datetime.now(datetime.timezone.utc) - created
            if age > datetime.timedelta(hours=max_age_hours):
                raise ValueError('Remote backup is too old')
            if age < -datetime.timedelta(minutes=5):
                raise ValueError('Remote backup timestamp is in the future')
            name = metadata['file']
            if (Path(name).name != name or not name.startswith('sub2api-') or
                    not name.endswith('.tar.age')):
                raise ValueError('Invalid backup filename')
            payload = work / 'bundle.age'
            digest = hashlib.sha256()
            with payload.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            if (payload.stat().st_size != metadata['bytes'] or
                    digest.hexdigest() != metadata['sha256']):
                raise ValueError('Received backup size/checksum mismatch')
            payload.replace(folder / name)
            metadata['received_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            (root / '.last-success.part').write_text(json.dumps(metadata, indent=2) + '\n')
            (root / '.last-success.part').replace(root / 'last-success.json')
        for old in sorted(folder.glob('sub2api-*.tar.age'), reverse=True)[keep:]:
            old.unlink()
    return metadata


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, help='SSH destination, for example backup@host')
    parser.add_argument('--identity', type=Path, required=True)
    parser.add_argument('--known-hosts', type=Path, required=True)
    parser.add_argument('--directory', type=Path, default=Path.home() / '.local/share/sub2api-backups')
    parser.add_argument('--proxy-command', help='Optional SSH ProxyCommand; direct connection by default')
    parser.add_argument('--keep', type=int, default=35)
    parser.add_argument('--max-age-hours', type=float, default=36)
    args = parser.parse_args()
    if (not args.host or args.host.startswith('-') or
            any(c.isspace() for c in args.host)):
        parser.error('Invalid SSH destination')
    if args.keep < 1 or not args.max_age_hours > 0:
        parser.error('Retention and maximum age must be positive')
    if not args.identity.is_file() or not args.known_hosts.is_file():
        parser.error('SSH identity and verified known_hosts files must exist')
    command = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
               '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=15',
               '-o', 'ServerAliveInterval=20', '-o', 'ServerAliveCountMax=3',
               '-o', 'UserKnownHostsFile=' + str(args.known_hosts.resolve())]
    if args.proxy_command:
        command += ['-o', 'ProxyCommand=' + args.proxy_command]
    command += ['-i', str(args.identity.resolve()), args.host]
    metadata = receive_backup(args.directory.resolve(), command, args.keep, args.max_age_hours)
    print(json.dumps(metadata))


if __name__ == '__main__':
    main()
