#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
import hashlib
import base64
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import elo_content as content
import elo_import as importer


class ImportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.destination = self.root / 'active'
        self.atom = {'schema_version': '0.2', 'content_id': 'record-1', 'title': 'Registro'}
        self.variant = {'variant_id': 'text-1', 'content_id': 'record-1',
                        'interaction': 'none', 'presentation': {
                            'title': 'Título ELO', 'text': 'Conteúdo real, sem rede.', 'media': []}}
        self.manifest = {'schema_version': '0.2', 'bundle_id': 'app.test',
                         'version': '1.2.3', 'title': 'Aplicação', 'atom_ids': ['record-1']}
        self.write('catalog/atoms/record.json', content.encoded(self.atom))
        self.write('catalog/variants/text.json', content.encoded(self.variant))
        self.seal()
        importer.import_bundle(self.source, self.destination, ['text-1'])
        self.previous = (self.destination / 'active.json').read_bytes()

    def write(self, name, data):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def seal(self):
        digest = hashlib.sha256()
        for path in sorted(self.source.rglob('*')):
            if path.is_file() and path.name != 'manifest.json':
                digest.update(path.relative_to(self.source).as_posix().encode())
                digest.update(path.read_bytes())
        self.manifest['content_hash'] = 'sha256:' + digest.hexdigest()
        self.write('manifest.json', content.encoded(self.manifest))

    def rejected(self, ids=None):
        with self.assertRaises(ValueError):
            importer.import_bundle(self.source, self.destination, ids or ['text-1'])
        self.assertEqual((self.destination / 'active.json').read_bytes(), self.previous)

    def test_import_and_restart_read_and_idempotence(self):
        active = content.read_active(self.destination)
        self.assertEqual(active['id'], 'app.test')
        self.assertEqual(active['pages'][0]['body'], self.variant['presentation']['text'])
        self.assertIn('1.2.3', active['name'])
        result = importer.import_bundle(self.source, self.destination, ['text-1'])
        self.assertEqual(result['result'], 'unchanged')
        self.assertEqual(result['source_hash'], self.manifest['content_hash'])

    def test_tampered_asset_and_catalog(self):
        self.write('assets/image.png', b'changed')
        self.rejected()
        self.seal()
        self.write('catalog/atoms/record.json', b'{}')
        self.rejected()

    def test_unsupported_capabilities_preserve_active(self):
        for change in ({'interaction': 'choose'}, {'presentation': {'title': 't', 'text': 'b', 'media': ['x']}},
                       {'presentation': {'title': 't', 'text': 'b', 'options': ['yes']}}):
            value = self.variant | change
            self.write('catalog/variants/text.json', content.encoded(value))
            self.seal()
            self.rejected()

    def test_selection_and_identity_validation(self):
        self.rejected(['missing'])
        self.rejected(['text-1', 'text-1'])
        self.manifest['atom_ids'] = []
        self.seal()
        self.rejected()
        self.manifest['atom_ids'] = ['other']
        self.seal()
        self.rejected()

    def test_bad_schema_duplicate_json_and_duplicate_identity(self):
        self.manifest['schema_version'] = '99'
        self.seal()
        self.rejected()
        self.manifest['schema_version'] = '0.2'
        self.write('catalog/variants/other.json', content.encoded(self.variant))
        self.seal()
        self.rejected()
        self.write('catalog/variants/other.json', b'{"variant_id":"a","variant_id":"b"}')
        self.seal()
        self.rejected()

    def test_symlinks_rejected_and_current_root_allowed(self):
        current = self.root / 'current'
        current.symlink_to(self.source, target_is_directory=True)
        self.assertEqual(importer.project(current, ['text-1'])[0], importer.project(self.source, ['text-1'])[0])
        (self.source / 'catalog' / 'outside').symlink_to(self.root, target_is_directory=True)
        self.rejected()

    def test_legacy_schema_and_variant_arrays(self):
        self.manifest['schema_version'] = '0.1'
        self.manifest['atom_ids'] = []
        second = self.variant | {'variant_id': 'text-2', 'presentation': {'title': 'Segundo', 'text': 'Outro'}}
        self.write('catalog/variants/text.json', content.encoded([self.variant, second]))
        self.seal()
        data, _ = importer.project(self.source, ['text-2', 'text-1'])
        self.assertEqual(content.decode(data)['pages'][0]['title'], 'Segundo')

    def test_image_projection_integrity_and_unsupported_media(self):
        raw = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aDXsAAAAASUVORK5CYII=')
        self.write('assets/images/test.png', raw)
        self.variant['presentation']['media'] = ['assets/images/test.png']
        self.write('catalog/variants/text.json', content.encoded(self.variant))
        self.seal()
        data, _ = importer.project(self.source, ['text-1'])
        value = content.fixture(data)
        self.assertEqual(value['version'], '2')
        image = value['pages'][0]['image']
        self.assertEqual(base64.b64decode(image['base64']), raw)
        self.assertEqual(image['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(image['alt'], 'Título ELO')
        importer.import_bundle(self.source, self.destination, ['text-1'])
        self.previous = (self.destination / 'active.json').read_bytes()
        for media in (['../outside.png'], ['https://example.com/x.png'], ['assets/missing.png'],
                      ['assets/images/test.png', 'assets/images/test.png'], ['assets/sound.mp3']):
            self.variant['presentation']['media'] = media
            self.write('catalog/variants/text.json', content.encoded(self.variant))
            self.seal()
            self.rejected()
        image['sha256'] = '0' * 64
        with self.assertRaises(ValueError): content.fixture(content.encoded(value))

    def test_client_bounds_rejected_before_activation(self):
        self.variant['presentation']['text'] = 'x' * 4097
        self.write('catalog/variants/text.json', content.encoded(self.variant))
        self.seal()
        self.rejected()


if __name__ == '__main__':
    unittest.main()
