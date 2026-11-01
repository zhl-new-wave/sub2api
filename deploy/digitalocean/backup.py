#!/usr/bin/env python3
"""Encrypted logical backup, with a full restore check in a temporary database.

Only an age public recipient is kept on this host. Keep the private identity
off-host. Redis is disposable cache. Freeze configuration edits while backing up.
"""

import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    os.umask(0o077)
    root = Path(__file__).resolve().parent
    folder = root / "backups"
    folder.mkdir(mode=0o700, exist_ok=True)
    lock = (root / '.backup.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    recipient = (root / 'backup-recipient.txt').read_text().strip()
    if not recipient.startswith('age1') or '\n' in recipient:
        raise SystemExit('Invalid public backup recipient')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name = 'sub2api-' + stamp + '.tar.age'
    destination = folder / name
    if destination.exists():
        raise SystemExit('Backup already exists for this second')
    pending = folder / (name + '.part')
    compose = ["docker", "compose", "-f", str(root / "compose.yaml")]
    if (root / '.https-enabled').exists():
        compose += ['-f', str(root / 'compose.https.yaml')]
    def run(command, **kwargs):
        return subprocess.run(command, cwd=root, check=True, **kwargs)
    with tempfile.TemporaryDirectory(prefix='.backup-work-', dir=root) as temp:
        work = Path(temp)
        with (work / "database.dump").open("xb") as output:
            subprocess.run(compose + ["exec", "-T", "postgres", "pg_dump", "-U", "sub2api", "-d", "sub2api", "-Fc"], cwd=root, stdout=output, check=True)
        verify_db = 'sub2api_restore_check_' + str(os.getpid())
        run(compose + ['exec', '-T', 'postgres', 'createdb', '-U', 'sub2api', verify_db])
        try:
            with (work / 'database.dump').open('rb') as source:
                run(compose + ['exec', '-T', 'postgres', 'pg_restore', '-U', 'sub2api', '--exit-on-error', '--no-owner', '--no-acl', '-d', verify_db], stdin=source)
            query = "SELECT json_build_object('tables',(SELECT count(*) FROM pg_tables WHERE schemaname='public'),'users',(SELECT count(*) FROM users),'accounts',(SELECT count(*) FROM accounts),'api_keys',(SELECT count(*) FROM api_keys),'usage_logs',(SELECT count(*) FROM usage_logs))"
            counts = json.loads(subprocess.check_output(compose + ['exec', '-T', 'postgres', 'psql', '-U', 'sub2api', '-d', verify_db, '-Atqc', query], cwd=root, text=True))
        finally:
            run(compose + ['exec', '-T', 'postgres', 'dropdb', '-U', 'sub2api', '--if-exists', verify_db])
        (work / 'database-validation.json').write_text(json.dumps({'full_restore': True, 'counts': counts}, indent=2) + '\n')
        with tarfile.open(work / 'configuration-and-app.tar.gz', 'w:gz') as archive:
            for path in sorted(root.iterdir()):
                if path.is_file() and path.name not in ['.backup.lock', 'migration-images.tar.gz']:
                    archive.add(path, arcname=path.name)
            for name in ['data/app', 'data/caddy', 'data/caddy-config']:
                if (root / name).exists(): archive.add(root / name, arcname=name)
        manifest = {}
        for path in sorted(work.iterdir()):
            manifest[path.name] = {'bytes': path.stat().st_size, 'sha256': sha256(path)}
        (work / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        with pending.open('xb') as encrypted:
            child = subprocess.Popen(['age', '-r', recipient], stdin=subprocess.PIPE, stdout=encrypted)
            try:
                with tarfile.open(fileobj=child.stdin, mode='w|') as archive:
                    for path in sorted(work.iterdir()): archive.add(path, arcname=path.name)
                child.stdin.close()
                if child.wait() != 0: raise RuntimeError('age encryption failed')
            finally:
                if child.poll() is None: child.kill(); child.wait()
            encrypted.flush()
            os.fsync(encrypted.fileno())
        pending.replace(destination)
    metadata = {'created_utc': stamp, 'file': destination.name, 'bytes': destination.stat().st_size,
                'sha256': sha256(destination), 'full_database_restore_verified': True, 'counts': counts}
    pending_metadata = folder / '.last-success.part'
    pending_metadata.write_text(json.dumps(metadata, indent=2) + '\n')
    pending_metadata.replace(folder / 'last-success.json')
    for old in sorted(folder.glob('sub2api-*.tar.age'), reverse=True)[30:]: old.unlink()
    print(json.dumps(metadata))


if __name__ == "__main__":
    main()
