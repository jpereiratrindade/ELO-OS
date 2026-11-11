#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
import base64
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from elo_content import activate, encoded, fixture, read_active
from elo_import import project_snapshot

class AudiovisualContentTest(unittest.TestCase):
    def setUp(self):
        output = io.BytesIO()
        with wave.open(output, 'wb') as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
            audio.writeframes(b'\0\0' * 1600)
        self.audio = output.getvalue()
        self.media = {'kind': 'audio', 'mime': 'audio/wav', 'sha256': hashlib.sha256(self.audio).hexdigest(),
                      'base64': base64.b64encode(self.audio).decode()}
        self.value = {'schema': 1, 'id': 'av-test', 'name': 'Audiovisual', 'version': '5',
                      'pages': [{'title': 'Escutar', 'body': 'Áudio local.', 'media': self.media}]}

    def test_v5_audio_roundtrip_and_offline_restart(self):
        data = encoded(self.value); fixture(data)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / 'staged.json').write_bytes(data)
            activate(root / 'cache', root / 'staged.json', len(data), hashlib.sha256(data).hexdigest())
            self.assertEqual(read_active(root / 'cache'), self.value)
            (root / 'staged.json').unlink()
            self.assertEqual(read_active(root / 'cache')['pages'][0]['media'], self.media)

    def test_reject_hash_mime_and_older_clients(self):
        for key, value in [('sha256', '0' * 64), ('mime', 'video/mp4'), ('base64', 'not base64')]:
            bad = self.value | {'pages': [self.value['pages'][0] | {'media': self.media | {key: value}}]}
            with self.subTest(key=key), self.assertRaises(ValueError): fixture(encoded(bad))
        with self.assertRaises(ValueError): fixture(encoded(self.value | {'version': '4', 'exposure_seconds': 15}))

    def test_v5_optional_automatic_exposure(self):
        fixture(encoded(self.value | {'exposure_seconds': 15}))
        with self.assertRaises(ValueError): fixture(encoded(self.value | {'exposure_seconds': 0}))

    def test_projects_published_atom_audio_without_losing_it(self):
        manifest = {'schema_version': '0.2', 'bundle_id': 'demo', 'version': '1', 'title': 'Demo', 'atom_ids': ['a']}
        files = {'catalog/atoms/a.json': encoded({'schema_version': '0.2', 'content_id': 'a', 'modalities': {'audio': ['sound.wav']}}),
                 'catalog/variants/v.json': encoded({'variant_id': 'v', 'content_id': 'a', 'interaction': 'none',
                       'presentation': {'title': 'Escutar', 'text': 'Conteúdo sonoro', 'media': []}}),
                 'assets/sound.wav': self.audio}
        data, _ = project_snapshot(manifest, files, ['v'])
        self.assertEqual(fixture(data)['pages'][0]['media']['sha256'], self.media['sha256'])
        self.assertEqual(fixture(data)['version'], '5')

if __name__ == '__main__': unittest.main()
