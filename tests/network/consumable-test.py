#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Real temporary PCM packages; corruption and unsafe input must never pass."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from elo_consumable import validate


class Packages(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        out = io.BytesIO()
        with wave.open(out, 'wb') as audio:
            audio.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            audio.writeframes(b'\0\0' * 1600)
        self.raw = out.getvalue()
        self.value = {
            'schema': 'elo-consumable-ingest/v1', 'production_id': 'prod_test',
            'production_version': '1.0.0', 'producer': {'system': 'sister-studio', 'release': 'test'},
            'title': 'Silêncio sintético', 'description': 'Fixture de PCM gerado pelo teste',
            'language': 'pt-BR', 'suggested_uses': ['teste'],
            'assets': [{'asset_id': 'audio', 'role': 'primary', 'kind': 'media.audio',
                        'filename': 'test.wav', 'mime': 'audio/wav', 'size_bytes': len(self.raw),
                        'sha256': hashlib.sha256(self.raw).hexdigest(), 'duration_ms': 100}],
            'provenance': {'declared_creator': 'teste', 'source_project_ref': 'test-project', 'reviewed': True},
            'rights': {'license': 'CC0-1.0', 'rights_holder': 'fixture-test', 'voice_permission': 'not-applicable'},
            'privacy': {'classification': 'public', 'purpose': 'catalogo-editorial-e-distribuicao'}}
        (self.root / 'test.wav').write_bytes(self.raw)
        self.write()

    def write(self):
        (self.root / 'manifest.json').write_text(json.dumps(self.value))

    def test_valid_read_only_and_metadata_identity(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        first = validate(self.root)
        self.assertEqual(first['status'], 'validated_locally')
        self.assertEqual(first, validate(self.root))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
        (self.root / 'manifest.json').write_text(json.dumps(self.value, indent=4, sort_keys=True))
        self.assertEqual(first, validate(self.root))
        self.value['rights']['license'] = 'CC-BY-4.0'
        self.write()
        self.assertNotEqual(first['manifest_sha256'], validate(self.root)['manifest_sha256'])

    def test_invalid_metadata(self):
        original = copy.deepcopy(self.value)
        cases = [('assets', 0, 'filename', '../test.wav'), ('assets', 0, 'filename', '/tmp/test.wav'),
                 ('assets', 0, 'sha256', '0' * 64), ('assets', 0, 'size_bytes', True),
                 ('assets', 0, 'duration_ms', 200), ('assets', 0, 'mime', 'audio/mpeg'),
                 ('provenance', 'reviewed', False), ('provenance', 'source_project_ref', '/private/project'),
                 ('rights', 'license', ''), ('rights', 'voice_permission', 'unknown'),
                 ('production_version', '01.0.0'), ('privacy', 'classification', 'private')]
        for *keys, value in cases:
            with self.subTest(keys=keys):
                self.value = copy.deepcopy(original)
                target = self.value
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                self.write()
                with self.assertRaises(ValueError):
                    validate(self.root)

    def test_symlink_and_special_file(self):
        media = self.root / 'test.wav'
        media.unlink()
        media.symlink_to('/dev/zero')
        with self.assertRaises((ValueError, OSError)):
            validate(self.root)
        media.unlink()
        import os
        os.mkfifo(media)
        with self.assertRaises(ValueError):
            validate(self.root)

    def test_corrupt_truncated_and_fake_wav(self):
        for raw in (self.raw[:-10], b'RIFF0000WAVE-not-a-wav', b'#!/bin/sh\necho bad'):
            with self.subTest(raw=raw[:12]):
                (self.root / 'test.wav').write_bytes(raw)
                self.value['assets'][0].update(size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                self.write()
                with self.assertRaises(ValueError):
                    validate(self.root)

    def test_extra_file_and_duplicate_json_key(self):
        extra = self.root / 'voice-profile.json'
        extra.write_text('{}')
        with self.assertRaises(ValueError):
            validate(self.root)
        extra.unlink()
        path = self.root / 'manifest.json'
        path.write_text(path.read_text().replace('{', '{"schema":"duplicate",', 1))
        with self.assertRaises(ValueError):
            validate(self.root)

    def test_cli(self):
        command = [sys.executable, str(ROOT / 'scripts/elo_consumable.py'), str(self.root)]
        good = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)['status'], 'validated_locally')
        (self.root / 'test.wav').unlink()
        bad = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertEqual(json.loads(bad.stdout)['status'], 'invalid_package')


if __name__ == '__main__':
    unittest.main()
