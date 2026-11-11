#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
import hashlib
import time
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from elo_content import encoded, decode
from elo_panel import Panel
from elo_server import server
from elo_receipts import Receipts


class PanelTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.bundle = root / 'bundle'
        files = {'catalog/atoms/a.json': {'schema_version': '0.2', 'content_id': 'a'},
                 'catalog/variants/v.json': [
                     {'variant_id': 'v1', 'content_id': 'a', 'interaction': 'none', 'presentation': {'title': 'Primeiro', 'text': 'Texto 1'}},
                     {'variant_id': 'v2', 'content_id': 'a', 'interaction': 'none', 'presentation': {'title': 'Segundo', 'text': 'Texto 2'}},
                     {'variant_id': 'v3', 'content_id': 'a', 'interaction': 'choose', 'presentation': {'title': 'Escolha', 'text': 'Texto 3'}}]}
        digest = hashlib.sha256()
        for name, value in sorted(files.items()):
            path = self.bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            data = encoded(value)
            path.write_bytes(data)
            digest.update(name.encode()); digest.update(data)
        self.hash = 'sha256:' + digest.hexdigest()
        (self.bundle / 'manifest.json').write_bytes(encoded({'schema_version': '0.2', 'bundle_id': 'app',
            'title': 'Teste', 'version': '1', 'atom_ids': ['a'], 'content_hash': self.hash}))
        self.panel = Panel(self.bundle, ['v1'], b'a' * 43, root / 'state/selection.json', ROOT / 'web/distribution', 9)
        self.service = server(self.bundle, ['v1'], b't' * 43, panel=self.panel)
        threading.Thread(target=self.service.serve_forever, daemon=True).start()
        self.addCleanup(self.stop)

    def stop(self):
        self.service.shutdown(); self.service.server_close()

    def request(self, path, method='GET', value=None, token=b'a' * 43, origin=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.service.server_port, timeout=5)
        headers = {'Content-Type': 'application/json'}
        if token: headers['Authorization'] = 'Bearer ' + token.decode()
        if origin: headers['Origin'] = origin
        connection.request(method, path, None if value is None else encoded(value), headers)
        response = connection.getresponse()
        status, body = response.status, response.read()
        connection.close()
        return status, body

    def test_public_landing_and_admin_auth_separation(self):
        self.assertEqual(self.request('/', token=None)[0], 200)
        self.assertEqual(self.request('/panel.js?v=release-test', token=None)[0], 200)
        self.assertEqual(self.request('/manage/status', token=None)[0], 401)
        self.assertEqual(self.request('/manage/status', token=b't' * 43)[0], 401)
        self.assertEqual(self.request('/v1/presentation', token=b'a' * 43)[0], 401)
        status, body = self.request('/manage/status')
        self.assertEqual(status, 200)
        self.assertFalse(decode(body)['studio_available'])
        self.assertFalse(decode(body)['variants'][2]['supported'])

    def test_selection_persists_and_changes_real_distribution(self):
        value = {'variants': ['v2', 'v1'], 'expected_hash': self.hash}
        self.assertEqual(self.request('/manage/selection', 'POST', value)[0], 200)
        status, body = self.request('/v1/presentation', token=b't' * 43)
        self.assertEqual(status, 200)
        self.assertEqual(decode(decode(body)['presentation'].encode())['pages'][0]['title'], 'Segundo')
        restored = Panel(self.bundle, ['v1'], b'a' * 43, self.panel.selection_file, self.panel.web_root)
        self.assertEqual(restored.variants(), ['v2', 'v1'])

    def test_exposure_persists_and_changes_delivery_digest(self):
        before = decode(self.panel.envelope())['sha256']
        self.panel.select({'variants': ['v1'], 'expected_hash': self.hash, 'exposure_seconds': 15})
        envelope = decode(self.panel.envelope())
        presentation = decode(envelope['presentation'].encode())
        self.assertEqual(presentation['version'], '4')
        self.assertEqual(presentation['exposure_seconds'], 15)
        self.assertNotEqual(envelope['sha256'], before)
        restored = Panel(self.bundle, ['v1'], b'a' * 43, self.panel.selection_file, self.panel.web_root)
        self.assertEqual(restored.exposure_seconds(), 15)
        for seconds in (True, 4, 3601, 2.5, '15', None):
            with self.assertRaises(ValueError):
                self.panel.select({'variants': ['v1'], 'expected_hash': self.hash, 'exposure_seconds': seconds})
        self.assertEqual(restored.exposure_seconds(), 15)
        self.panel.select({'variants': ['v1'], 'expected_hash': self.hash, 'exposure_seconds': 0})
        self.assertEqual(decode(self.panel.envelope())['sha256'], before)

    def test_individual_terminals_isolate_status_and_revocation(self):
        status, body = self.request('/manage/terminals', 'POST', {'name': 'Recepção'})
        self.assertEqual(status, 201)
        first = decode(body)
        second = decode(self.request('/manage/terminals', 'POST', {'name': 'Sala 2'})[1])
        self.assertNotEqual(first['id'], second['id'])
        self.assertNotIn(first['token'], self.panel.terminals.path.read_text())
        report = {'schema': 2, 'session': '12345678-1234-1234-1234-123456789abc', 'sequence': 1,
            'received_sha256': 'a' * 64, 'presented_sha256': 'a' * 64,
            'display': {'publication': 'Pampa v1', 'title': 'Campos Sulinos', 'page': 2, 'pages': 3,
                        'mode': 'automatic', 'exposure_seconds': 15}}
        self.assertEqual(self.request('/v1/receipt', 'POST', report, token=first['token'].encode())[0], 200)
        devices = decode(self.request('/manage/terminals')[1])
        one = next(d for d in devices if d['id'] == first['id'])
        two = next(d for d in devices if d['id'] == second['id'])
        self.assertEqual(one['display']['title'], 'Campos Sulinos')
        self.assertTrue(one['recent'])
        self.assertIsNone(two['last_seen'])
        self.assertNotIn(first['token'], encoded(devices).decode())
        self.assertEqual(self.request('/manage/status', token=first['token'].encode())[0], 401)
        self.assertEqual(self.request('/manage/terminals/' + first['id'] + '/revoke', 'POST', {})[0], 200)
        self.assertEqual(self.request('/v1/presentation', token=first['token'].encode())[0], 401)
        self.assertEqual(self.request('/v1/receipt', 'POST', report, token=first['token'].encode())[0], 401)
        self.assertEqual(self.request('/v1/presentation', token=second['token'].encode())[0], 200)
        restored = Panel(self.bundle, ['v1'], b'a' * 43, self.panel.selection_file, self.panel.web_root)
        self.assertIsNone(restored.terminals.authenticate(first['token'].encode()))
        self.assertEqual(restored.terminals.authenticate(second['token'].encode()), second['id'])

    def test_invalid_display_report_cannot_replace_last_confirmed_page(self):
        value = {'schema': 2, 'session': '12345678-1234-1234-1234-123456789abc', 'sequence': 1,
            'received_sha256': 'a' * 64, 'presented_sha256': 'a' * 64,
            'display': {'publication': 'ELO', 'title': 'Página', 'page': 1, 'pages': 2,
                        'mode': 'automatic', 'exposure_seconds': 15}}
        self.assertEqual(self.request('/v1/receipt', 'POST', value, token=b't' * 43)[0], 200)
        for change in ({'page': 3}, {'pages': 0}, {'exposure_seconds': 0}, {'title': 'x' * 257}, {'mode': 'unknown'}):
            invalid = dict(value, sequence=2, display=value['display'] | change)
            self.assertEqual(self.request('/v1/receipt', 'POST', invalid, token=b't' * 43)[0], 400)
        self.assertEqual(self.panel.receipts.record['sequence'], 1)
        expired = self.panel.receipts.status('a' * 64, now=time.time()+100)
        self.assertFalse(expired['recent'])
        self.assertEqual(expired['display']['title'], 'Página')

    def test_invalid_stale_or_unsupported_selection_never_changes_state(self):
        for variants, expected in ((['v3'], self.hash), (['v1'], 'stale'), ([], self.hash), (['v1', 'v1'], self.hash)):
            self.assertEqual(self.request('/manage/selection', 'POST', {'variants': variants, 'expected_hash': expected})[0], 400)
            self.assertFalse(self.panel.selection_file.exists())
            self.assertEqual(self.panel.variants(), ['v1'])

    def test_cross_origin_changes_rejected_and_terminal_cannot_upload(self):
        self.assertEqual(self.request('/manage/selection', 'POST', {'variants': ['v2'], 'expected_hash': self.hash}, origin='https://evil.example')[0], 403)
        self.assertEqual(self.request('/api/upload', 'POST', {}, token=b't' * 43)[0], 401)
        self.assertFalse(self.panel.selection_file.exists())

    def test_real_receipt_endpoint_separates_received_from_presented(self):
        status, payload = self.request('/v1/presentation', token=b't' * 43)
        digest = decode(payload)['sha256']
        report = {'schema': 1, 'session': '12345678-1234-1234-1234-123456789abc',
                  'sequence': 1, 'received_sha256': digest, 'presented_sha256': ''}
        self.assertEqual(self.request('/v1/receipt', 'POST', report)[0], 401)
        self.assertEqual(self.request('/v1/receipt', 'POST', report, token=b't' * 43)[0], 200)
        self.assertEqual(decode(self.request('/manage/delivery')[1])['state'], 'received')
        seen = self.panel.receipts.record['seen_at']
        self.assertEqual(self.request('/v1/receipt', 'POST', report, token=b't' * 43)[0], 200)
        self.assertEqual(self.panel.receipts.record['seen_at'], seen)
        report.update(sequence=2, presented_sha256=digest)
        self.assertEqual(self.request('/v1/receipt', 'POST', report, token=b't' * 43)[0], 200)
        self.assertEqual(decode(self.request('/manage/delivery')[1])['state'], 'presented')
        self.assertEqual(self.panel.receipts.status(digest, now=time.time()+100)['state'], 'stale')
        restored = Receipts(self.panel.receipts.path)
        self.assertEqual(restored.status(digest)['state'], 'presented')
        report['sequence'] = 1
        self.assertEqual(self.request('/v1/receipt', 'POST', report, token=b't' * 43)[0], 400)

    def test_invalid_receipts_never_create_delivery_confirmation(self):
        for value in ({}, {'schema': 99}, {'schema': 1, 'session': 'x', 'sequence': 1,
                      'received_sha256': '../bad', 'presented_sha256': ''}):
            self.assertEqual(self.request('/v1/receipt', 'POST', value, token=b't' * 43)[0], 400)
        self.assertEqual(decode(self.request('/manage/delivery')[1])['state'], 'unconfirmed')

    def test_media_session_is_limited_to_assets(self):
        self.assertFalse(self.panel.media_authorized(None))
        self.assertFalse(self.panel.media_authorized('elo_media=wrong'))
        self.assertTrue(self.panel.media_authorized('elo_media=' + self.panel.media_cookie()))
        self.assertEqual(self.request('/studio/assets/images/test.png', token=None)[0], 401)
        self.assertEqual(self.request('/manage/logout', 'POST')[0], 200)

    def test_fixed_editorial_proxy_preserves_body_and_separate_credential(self):
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                received.append((self.path, self.headers.get('Authorization'), self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(201); self.end_headers(); self.wfile.write(b'{"success":true}')
        upstream = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=upstream.serve_forever, daemon=True).start()
        try:
            self.panel.studio_port = upstream.server_port
            self.assertEqual(self.request('/api/upload', 'POST', {'filename': 'test.png'})[0], 201)
            self.assertEqual(received, [('/api/upload', 'Bearer ' + 'a' * 43, encoded({'filename': 'test.png'}))])
            with self.assertRaises(ValueError):
                self.panel.proxy('GET', 'http://evil.example/api/status', b'', 'application/json')
        finally:
            upstream.shutdown(); upstream.server_close()


if __name__ == '__main__':
    unittest.main()
