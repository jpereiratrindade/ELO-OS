#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Negative checks for the host image gate, using tiny synthetic images."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "preflight", Path(__file__).resolve().parents[2] / "scripts/pi5-preflight.py")
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class ImageGate(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.image = Path(self.directory.name) / "sdcard.img"
        self.data = bytearray(32 * 512)
        self.data[510:512] = b"\x55\xaa"
        for index, kind, start, sectors in ((0, 0x0C, 1, 8), (1, 0x83, 9, 23)):
            self.data[446 + 16 * index + 4] = kind
            struct.pack_into("<II", self.data, 446 + 16 * index + 8, start, sectors)
        self.data[512 + 510:512 + 512] = b"\x55\xaa"
        self.data[512 + 82:512 + 90] = b"FAT32   "
        struct.pack_into("<H", self.data, 512 + 11, 512)
        self.data[9 * 512 + 1024 + 56:9 * 512 + 1024 + 58] = b"\x53\xef"
        struct.pack_into("<I", self.data, 9 * 512 + 1024 + 96, 0x40)

    def inspect(self, expected=None):
        self.image.write_bytes(self.data)
        before = self.image.read_bytes()
        try:
            return preflight.inspect(self.image, expected or hashlib.sha256(before).hexdigest())
        finally:
            self.assertEqual(self.image.read_bytes(), before)

    def test_report_does_not_claim_physical_boot(self):
        report = self.inspect()
        self.assertEqual(report["physical_boot"], "NOT_TESTED")
        self.assertEqual(report["image_source_revision"], "NOT_RECORDED")

    def test_wrong_hash(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 divergente"):
            self.inspect("0" * 64)

    def test_bad_mbr(self):
        self.data[510] = 0
        with self.assertRaisesRegex(ValueError, "MBR"):
            self.inspect()

    def test_out_of_bounds(self):
        struct.pack_into("<I", self.data, 462 + 12, 100)
        with self.assertRaisesRegex(ValueError, "limites"):
            self.inspect()

    def test_overlap(self):
        struct.pack_into("<I", self.data, 462 + 8, 8)
        with self.assertRaisesRegex(ValueError, "sobrepostas"):
            self.inspect()

    def test_extra_partition(self):
        self.data[478 + 4] = 0x83
        with self.assertRaisesRegex(ValueError, "duas partições"):
            self.inspect()

    def test_bad_filesystem_signatures(self):
        for offset, message in ((512 + 82, "FAT"), (9 * 512 + 1024 + 56, "ext4")):
            with self.subTest(message=message):
                original = self.data[offset]
                self.data[offset] = 0
                with self.assertRaisesRegex(ValueError, message):
                    self.inspect()
                self.data[offset] = original

    def test_fat16_volume_in_fat32_mbr_entry_is_reported(self):
        self.data[512 + 82:512 + 90] = b"\0" * 8
        self.data[512 + 54:512 + 62] = b"FAT16   "
        report = self.inspect()
        self.assertEqual(report["partitions"][0]["type"], "0x0c")
        self.assertEqual(report["partitions"][0]["filesystem_signature"], "FAT16")
        self.assertTrue(report["notes"])

    def test_non_regular_path(self):
        with self.assertRaisesRegex(ValueError, "arquivo de imagem regular"):
            preflight.inspect(Path(self.directory.name), "0" * 64)


if __name__ == "__main__":
    unittest.main()
