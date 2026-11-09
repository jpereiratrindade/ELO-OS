#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
import errno
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import elo_content as content


class ActivationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'content'
        self.first = self.source('first')
        self.second = self.source('second')
        self.publish(self.first)

    def source(self, identity):
        value = json.loads((ROOT / 'tests/client/fixtures/local.json').read_text())
        value['id'] = identity
        value['pages'][0]['title'] = identity
        path = self.base / f'{identity}.json'
        path.write_bytes(content.encoded(value))
        return path

    def publish(self, path, **kwargs):
        data = path.read_bytes()
        return content.activate(self.root, path, len(data), hashlib.sha256(data).hexdigest(), **kwargs)

    def identity(self):
        return content.read_active(self.root)['id']

    def test_activation_idempotence_and_explicit_return_to_old_bundle(self):
        self.assertEqual(self.identity(), 'first')
        self.assertEqual(self.publish(self.first), 'unchanged')
        self.assertEqual(self.publish(self.second), 'activated')
        self.assertEqual(self.identity(), 'second')
        self.assertEqual(self.publish(self.first), 'activated')
        self.assertEqual(self.identity(), 'first')
        self.assertEqual(len(list((self.root / 'bundles').iterdir())), 2)

    def test_truncated_and_wrong_hash_leave_previous_active(self):
        data = self.second.read_bytes()
        for size, digest in ((len(data) + 1, hashlib.sha256(data).hexdigest()), (len(data), '0' * 64)):
            with self.assertRaises(ValueError):
                content.activate(self.root, self.second, size, digest)
            self.assertEqual(self.identity(), 'first')

    def test_structurally_invalid_but_correctly_hashed_input_is_rejected(self):
        for data in (b'{', b'{}', b'{"schema":1,"schema":1}', b'x' * (content.MAX_CONTENT + 1)):
            self.second.write_bytes(data)
            with self.assertRaises(ValueError):
                self.publish(self.second)
            self.assertEqual(self.identity(), 'first')

    def test_out_of_space_during_write_preserves_active(self):
        with patch.object(content, 'write_file', side_effect=OSError(errno.ENOSPC, 'injected no space')):
            with self.assertRaises(OSError):
                self.publish(self.second)
        self.assertEqual(self.identity(), 'first')

    def test_staged_bytes_are_rechecked_before_publication(self):
        def corrupt(point):
            if point == 'after-staged-write':
                next(self.root.glob('.staged-*/presentation.json')).write_bytes(b'truncated')
        with self.assertRaises(ValueError):
            self.publish(self.second, fault=corrupt)
        self.assertEqual(self.identity(), 'first')

    def test_failures_before_publication_preserve_active(self):
        for point in ('before-bundle-rename', 'after-bundle-rename', 'before-pointer-rename'):
            def fail(current):
                if current == point:
                    raise OSError(errno.EIO, point)
            with self.assertRaises(OSError):
                self.publish(self.second, fault=fail)
            self.assertEqual(self.identity(), 'first')

    def test_failure_after_publication_is_uncertain_not_a_fake_rollback(self):
        def fail(point):
            if point == 'after-pointer-rename':
                raise OSError(errno.EIO, point)
        with self.assertRaises(content.ActivationUncertain):
            self.publish(self.second, fault=fail)
        self.assertEqual(self.identity(), 'second')
        self.assertEqual(self.publish(self.second), 'unchanged')
        self.publish(self.first)
        self.assertEqual(self.identity(), 'first')

    def test_corrupted_reused_bundle_is_never_published(self):
        digest = hashlib.sha256(self.first.read_bytes()).hexdigest()
        self.publish(self.second)
        (self.root / 'bundles' / digest / 'presentation.json').write_bytes(b'truncated')
        with self.assertRaises(ValueError):
            self.publish(self.first)
        self.assertEqual(self.identity(), 'second')

    def test_path_traversal_and_symlinks_are_rejected(self):
        (self.root / 'active.json').write_bytes(content.encoded({'bundle': '../outside'}))
        with self.assertRaises(ValueError):
            content.read_active(self.root)
        self.publish(self.first)
        digest = hashlib.sha256(self.first.read_bytes()).hexdigest()
        payload = self.root / 'bundles' / digest / 'presentation.json'
        payload.unlink()
        payload.symlink_to(self.first)
        with self.assertRaises(ValueError):
            content.read_active(self.root)

    def test_utf8_byte_limits_and_nul(self):
        for title in ('é' * 129, 'hidden\0title'):
            value = json.loads(self.second.read_text())
            value['pages'][0]['title'] = title
            self.second.write_bytes(content.encoded(value))
            with self.assertRaises(ValueError):
                self.publish(self.second)
            self.assertEqual(self.identity(), 'first')

    def test_readers_observe_complete_old_or_new_bundles(self):
        stop = threading.Event()
        observed = threading.Event()
        def read():
            count = 0
            while not stop.is_set():
                value = content.read_active(self.root)
                self.assertIn(value['id'], ('first', 'second'))
                self.assertEqual(value['id'], value['pages'][0]['title'])
                count += 1
                observed.set()
            return count
        with ThreadPoolExecutor(max_workers=1) as pool:
            reader = pool.submit(read)
            try:
                self.assertTrue(observed.wait(timeout=2))
                for path in (self.second, self.first) * 5:
                    self.publish(path)
            finally:
                stop.set()
            self.assertGreater(reader.result(timeout=2), 0)


if __name__ == '__main__':
    unittest.main()
