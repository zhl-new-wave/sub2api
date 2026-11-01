"""Exercise backup integrity failures without network access or real secrets."""

import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('backup_pull', Path(__file__).with_name('backup-pull.py'))
backup_pull = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup_pull)


class BackupPullTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = b'synthetic encrypted backup bytes'
        self.metadata = {
            'created_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
            'file': 'sub2api-test.tar.age',
            'bytes': len(self.payload),
            'sha256': hashlib.sha256(self.payload).hexdigest(),
        }

    def receive(self, unexpected_member=None):
        export = self.root / 'export.tar'
        with tarfile.open(export, 'w') as archive:
            entries = {'bundle.age': self.payload, 'metadata.json': json.dumps(self.metadata).encode()}
            if unexpected_member:
                entries[unexpected_member] = b'unsafe'
            for name, payload in entries.items():
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
        command = [sys.executable, '-c', 'import pathlib,sys;sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())', str(export)]
        return backup_pull.receive_backup(self.root / 'receiver', command)

    def assert_not_published(self):
        self.assertFalse((self.root / 'receiver/last-success.json').exists())
        self.assertEqual(list((self.root / 'receiver/backups').iterdir()), [])

    def test_valid_copy_is_published_with_metadata(self):
        result = self.receive()
        self.assertEqual((self.root / 'receiver/backups/sub2api-test.tar.age').read_bytes(), self.payload)
        self.assertIn('received_utc', result)
        self.assertEqual(json.loads((self.root / 'receiver/last-success.json').read_text()), result)

    def test_corrupt_payload_is_rejected(self):
        self.payload += b'corruption'
        with self.assertRaisesRegex(ValueError, 'size/checksum'):
            self.receive()
        self.assert_not_published()

    def test_stale_backup_is_rejected(self):
        self.metadata['created_utc'] = '20200101T000000Z'
        with self.assertRaisesRegex(ValueError, 'too old'):
            self.receive()
        self.assert_not_published()

    def test_future_timestamp_is_rejected(self):
        self.metadata['created_utc'] = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).strftime('%Y%m%dT%H%M%SZ')
        with self.assertRaisesRegex(ValueError, 'future'):
            self.receive()
        self.assert_not_published()

    def test_path_traversal_filename_is_rejected(self):
        self.metadata['file'] = '../sub2api-stolen.tar.age'
        with self.assertRaisesRegex(ValueError, 'filename'):
            self.receive()
        self.assert_not_published()

    def test_unexpected_archive_member_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'export content'):
            self.receive('../outside.txt')
        self.assert_not_published()
        self.assertFalse((self.root / 'outside.txt').exists())


if __name__ == '__main__':
    unittest.main()
