#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Provision only new regular files; never overwrite an existing path."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(shutil.which('mkfs.ext4'), 'host e2fsprogs unavailable')
class DataImageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='elo-data-image-test-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.image = self.directory / 'data.ext4'
        self.env = {**os.environ, 'PROFILE': 'qemu-x86_64-appliance',
                    'OUTPUT_DIR': str(self.directory / 'output'),
                    'QEMU_DATA_IMAGE': str(self.image), 'DATA_SIZE_MIB': '32'}

    def run_script(self, **overrides):
        return subprocess.run([str(ROOT / 'scripts/create-data-image.sh')],
                              env={**self.env, **overrides},
                              capture_output=True, text=True)

    def test_new_ext4_has_expected_label_and_size(self):
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.image.stat().st_size, 32 * 1024 * 1024)
        with self.image.open('rb') as stream:
            stream.seek(1024 + 56)
            self.assertEqual(stream.read(2), b'\x53\xef')
            stream.seek(1024 + 120)
            self.assertEqual(stream.read(16).rstrip(b'\0'), b'ELO_DATA')

    def test_existing_file_is_preserved(self):
        self.image.write_bytes(b'previous data')
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertEqual(self.image.read_bytes(), b'previous data')

    def test_dangling_symlink_is_not_followed(self):
        target = self.directory / 'must-not-be-created'
        self.image.symlink_to(target)
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertFalse(target.exists())
        self.assertTrue(self.image.is_symlink())

    def test_device_and_non_appliance_profile_are_refused(self):
        self.assertNotEqual(self.run_script(QEMU_DATA_IMAGE='/dev/null').returncode, 0)
        self.assertEqual(self.run_script(PROFILE='pi5').returncode, 2)
        self.assertFalse(self.image.exists())

    def test_invalid_sizes_never_create_an_image(self):
        for size in ('0', '31', '4097', '-1', '32M', '0032'):
            with self.subTest(size=size):
                self.assertEqual(self.run_script(DATA_SIZE_MIB=size).returncode, 2)
                self.assertFalse(self.image.exists())

    def test_launcher_refuses_system_artifact_aliases_and_devices(self):
        output = Path(self.env['OUTPUT_DIR'])
        images = output / 'images'
        images.mkdir(parents=True)
        (output / '.config').write_text(
            f'BR2_DEFCONFIG="{ROOT}/configs/elo_qemu_x86_64_appliance_defconfig"\nBR2_x86_64=y\n')
        for name in ('bzImage', 'rootfs.ext4'):
            (images / name).write_bytes(b'protected system artifact')
        alias = self.directory / 'alias.ext4'
        os.link(images / 'rootfs.ext4', alias)
        emulator = self.directory / 'qemu-mock'
        emulator.write_text('#!/bin/sh\nexit 77\n')
        emulator.chmod(0o755)
        for path in (images / 'rootfs.ext4', images / 'bzImage', alias, Path('/dev/null')):
            with self.subTest(path=path):
                proc = subprocess.run([str(ROOT / 'scripts/run-qemu.sh')],
                    env={**self.env, 'QEMU': str(emulator), 'QEMU_DATA_IMAGE': str(path)},
                    capture_output=True, text=True)
                self.assertEqual(proc.returncode, 1, proc.stderr)
        self.image.write_bytes(b'independent data disk')
        proc = subprocess.run([str(ROOT / 'scripts/run-qemu.sh')],
            env={**self.env, 'QEMU': str(emulator)}, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 77, proc.stderr)


if __name__ == '__main__':
    unittest.main()
