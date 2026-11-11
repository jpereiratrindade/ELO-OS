#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Real HTTP/TLS intake with isolated disk state; never touches installed services."""
import concurrent.futures
import base64
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from elo_content import encoded, decode
from elo_ingest import Ingest, IngestError
from elo_panel import Panel
from elo_server import server


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixture_module = load('consumable_fixture', ROOT / 'tests/network/consumable-test.py')
Publisher = load('publisher', ROOT / 'scripts/publish-consumable.py').Publisher
TOKEN, TERMINAL, ADMIN = b'i' * 43, b't' * 43, b'a' * 43
BASE = '/v1/ingest/submissions'


class IntakeTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.Packages()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ingest = Ingest(self.root / 'intake', TOKEN, 'studio-1')
        self.panel = Panel(self.root / 'bundle', [], ADMIN, self.root / 'selection.json', ROOT / 'web/distribution')
        self.service = server(None, [], TERMINAL, panel=self.panel, ingest=self.ingest)
        threading.Thread(target=self.service.serve_forever, daemon=True).start()
        self.addCleanup(self.stop)

    def stop(self):
        self.service.shutdown()
        self.service.server_close()

    def request(self, path=BASE, method='POST', value=None, raw=None, token=TOKEN, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.service.server_port, timeout=5)
        body = encoded(value) if value is not None else (raw or b'')
        headers = {'Content-Type': 'application/json', 'Idempotency-Key': 'request-1',
                   **({'Authorization': 'Bearer ' + token.decode()} if token else {}), **(headers or {})}
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        status, result = response.status, decode(response.read())
        connection.close()
        return status, result

    def stage(self):
        status, receipt = self.request(value=self.fixture.value)
        self.assertEqual(status, 201)
        self.assertEqual(receipt['status'], 'staged')
        return BASE + '/' + receipt['submission_id']

    def upload(self, base, raw=None):
        return self.request(base + '/assets/audio', 'PUT', raw=self.fixture.raw if raw is None else raw,
                            headers={'Content-Type': 'audio/wav'})

    def test_auth_separation_and_disabled_by_default(self):
        for token in (None, TERMINAL, ADMIN):
            self.assertEqual(self.request(value=self.fixture.value, token=token)[0], 401)
        self.assertEqual(self.request('/manage/ingest', 'GET')[0], 401)
        self.assertEqual(self.request('/manage/ingest', 'GET', token=ADMIN)[0], 200)
        self.assertEqual(self.request('/v1/presentation', 'GET')[0], 401)
        self.assertEqual(self.request('/api/atoms', 'POST', value={}, token=TOKEN)[0], 401)
        disabled = server(None, [], TERMINAL)
        threading.Thread(target=disabled.serve_forever, daemon=True).start()
        try:
            connection = http.client.HTTPConnection('127.0.0.1', disabled.server_port, timeout=5)
            connection.request('POST', BASE, b'{}')
            response = connection.getresponse()
            self.assertEqual(response.status, 404)
            response.read()
            connection.close()
        finally:
            disabled.shutdown()
            disabled.server_close()
        for token in (TERMINAL, ADMIN):
            store = Ingest(self.root / ('collision-' + token[:1].decode()), token, 'studio')
            with self.assertRaises(ValueError):
                server(None, [], TERMINAL, panel=self.panel, ingest=store)

    def test_lifecycle_persistence_and_read_only_distribution(self):
        base = self.stage()
        self.assertEqual(self.request(base + '/commit')[1]['error'], 'assets_missing')
        self.assertEqual(self.upload(base)[0], 200)
        status, receipt = self.request(base + '/commit')
        self.assertEqual(status, 200)
        self.assertEqual(receipt['status'], 'quarantined')
        self.assertIsNone(receipt['consumable_id'])
        self.assertEqual(receipt['pending_reason'], 'editorial_integration_required')
        self.assertEqual(self.request(base + '/commit')[1], receipt)
        self.assertEqual(self.upload(base)[1], receipt)
        restored = Ingest(self.root / 'intake', TOKEN, 'studio-1')
        self.assertEqual(restored.get(receipt['submission_id']), receipt)
        self.assertEqual(self.request(base, 'GET')[1], receipt)
        self.assertFalse((self.root / 'selection.json').exists())
        self.assertFalse((self.root / 'editorial.sqlite3').exists())

    def test_idempotency_conflicts_and_producer_scope(self):
        base = self.stage()
        for key in ('request-1', 'another-key'):
            status, receipt = self.request(value=self.fixture.value, headers={'Idempotency-Key': key})
            self.assertEqual(status, 200)
            self.assertTrue(base.endswith(receipt['submission_id']))
        self.fixture.value['rights']['license'] = 'CC-BY-4.0'
        self.assertEqual(self.request(value=self.fixture.value)[1]['error'], 'idempotency_conflict')
        self.assertEqual(self.request(value=self.fixture.value, headers={'Idempotency-Key': 'fresh-key'})[1]['error'],
                         'production_version_conflict')
        self.fixture.value['production_version'] = '1.0.1'
        self.assertEqual(self.request(value=self.fixture.value, headers={'Idempotency-Key': 'new-version'})[0], 201)
        other = Ingest(self.root / 'intake', b'o' * 43, 'studio-2')
        with self.assertRaises(IngestError):
            other.get(base.rsplit('/', 1)[1])
        self.assertNotEqual(other.create(self.fixture.value, 'new-version')[0]['submission_id'],
                            self.request(value=self.fixture.value, headers={'Idempotency-Key': 'new-version'})[1]['submission_id'])

    def test_parallel_retries_do_not_duplicate(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda _: self.request(value=self.fixture.value), range(16)))
        self.assertEqual(sum(status == 201 for status, _ in results), 1)
        self.assertEqual(len({value['submission_id'] for _, value in results}), 1)

    def test_manual_package_import_and_private_audio_preview(self):
        package = {'schema': 'elo-consumable-package/v1', 'manifest': self.fixture.value,
                   'asset_base64': base64.b64encode(self.fixture.raw).decode()}
        for token in (None, TOKEN, TERMINAL):
            self.assertEqual(self.request('/manage/ingest/import', value=package, token=token)[0], 401)
        status, receipt = self.request('/manage/ingest/import', value=package, token=ADMIN)
        self.assertEqual(status, 200)
        self.assertEqual(receipt['status'], 'quarantined')
        self.assertEqual(self.request('/manage/ingest/import', value=package, token=ADMIN)[1], receipt)
        summary = self.request('/manage/ingest', 'GET', token=ADMIN)[1]['submissions'][0]
        self.assertEqual(summary['title'], self.fixture.value['title'])
        path = '/manage/ingest/' + receipt['submission_id'] + '/audio'
        self.assertEqual(self.request(path, 'GET', token=TOKEN)[0], 401)
        connection = http.client.HTTPConnection('127.0.0.1', self.service.server_port, timeout=5)
        connection.request('GET', path, headers={'Authorization': 'Bearer ' + ADMIN.decode()})
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader('Content-Type'), 'audio/wav')
        self.assertEqual(response.read(), self.fixture.raw)
        connection.close()
        package['asset_base64'] = base64.b64encode(b'bad').decode()
        self.assertEqual(self.request('/manage/ingest/import', value=package, token=ADMIN)[0], 422)

    def test_integrity_codec_and_upload_path_rejection(self):
        base = self.stage()
        self.assertEqual(self.upload(base, self.fixture.raw[:-1])[0], 422)
        self.assertEqual(self.upload(base, b'x' * len(self.fixture.raw))[1]['error'], 'asset_integrity_mismatch')
        self.assertEqual(self.request(base + '/assets/../other', 'PUT', raw=b'x')[0], 404)
        # Valid digest of an invalid WAV passes byte upload, then is permanently rejected at commit.
        raw = b'RIFF0000WAVE-not-a-wav'
        self.fixture.value['production_version'] = '1.0.1'
        self.fixture.value['assets'][0].update(size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        status, receipt = self.request(value=self.fixture.value, headers={'Idempotency-Key': 'invalid-codec'})
        self.assertEqual(status, 201)
        base = BASE + '/' + receipt['submission_id']
        self.assertEqual(self.upload(base, raw)[0], 200)
        status, rejected = self.request(base + '/commit')
        self.assertEqual(rejected['status'], 'rejected')
        self.assertEqual(rejected['rejections'], [{'code': 'invalid_audio_payload'}])
        self.assertEqual(self.request(base + '/commit')[1], rejected)

    def test_manifest_origin_limits_and_quotas(self):
        self.assertEqual(self.request(value=self.fixture.value, headers={'Origin': 'http://evil.test'})[0], 403)
        self.assertEqual(self.request(raw=b'{}', headers={'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.request(raw=b'x' * 65537)[0], 413)
        self.fixture.value['assets'][0]['filename'] = '../test.wav'
        self.assertEqual(self.request(value=self.fixture.value)[0], 422)
        self.fixture.value['assets'][0]['filename'] = 'test.wav'
        store = Ingest(self.root / 'limited', TOKEN, 'studio', max_submissions=1, max_bytes=8388608)
        store.create(self.fixture.value, 'one')
        self.fixture.value['production_version'] = '1.0.1'
        with self.assertRaises(IngestError) as caught:
            store.create(self.fixture.value, 'two')
        self.assertEqual(caught.exception.status, 429)

    def test_duplicate_headers_and_symlink_spool(self):
        for header in ('Content-Length: 2\r\nContent-Length: 2', 'Transfer-Encoding: chunked',
                       'Authorization: Bearer ' + TOKEN.decode()):
            with socket.create_connection(('127.0.0.1', self.service.server_port), timeout=5) as connection:
                connection.sendall(('POST ' + BASE + ' HTTP/1.0\r\nAuthorization: Bearer ' + TOKEN.decode()
                                    + '\r\n' + header + '\r\n\r\n{}').encode())
                response = connection.recv(4096)
                self.assertTrue(response.startswith((b'HTTP/1.0 400', b'HTTP/1.0 401')), response)
        base = self.stage()
        sid = base.rsplit('/', 1)[1]
        outside = self.root / 'outside'
        outside.write_bytes(b'preserve')
        (self.root / 'intake' / (sid + '.wav')).symlink_to(outside)
        self.assertEqual(self.upload(base)[0], 409)
        self.assertEqual(outside.read_bytes(), b'preserve')

    def test_cli_https_with_verified_certificate_and_retries(self):
        key, cert = self.root / 'server.key', self.root / 'server.crt'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                        '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)
        tls = server(None, [], TERMINAL, ingest=self.ingest)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        tls.socket = context.wrap_socket(tls.socket, server_side=True)
        threading.Thread(target=tls.serve_forever, daemon=True).start()
        try:
            endpoint = f'https://localhost:{tls.server_port}'
            publisher = Publisher(endpoint, TOKEN, cert)
            first = publisher.publish(self.fixture.root)
            self.assertEqual(first['status'], 'quarantined')
            self.assertEqual(publisher.publish(self.fixture.root), first)
            with self.assertRaises(ssl.SSLCertVerificationError):
                Publisher(endpoint, TOKEN).publish(self.fixture.root)
            with self.assertRaises(ssl.SSLCertVerificationError):
                Publisher(f'https://127.0.0.1:{tls.server_port}', TOKEN, cert).publish(self.fixture.root)
            token_file = self.root / 'ingest.token'
            token_file.write_bytes(TOKEN)
            token_file.chmod(0o600)
            cli = subprocess.run([sys.executable, str(ROOT / 'scripts/publish-consumable.py'), str(self.fixture.root),
                                  '--endpoint', endpoint, '--token-file', str(token_file), '--certificate', str(cert)],
                                 capture_output=True, text=True)
            self.assertEqual(cli.returncode, 0, cli.stderr)
            self.assertEqual(json.loads(cli.stdout), first)
            with self.assertRaises(ValueError):
                Publisher('http://example.com', TOKEN, allow_loopback_http=True)
        finally:
            tls.shutdown()
            tls.server_close()


if __name__ == '__main__':
    unittest.main()
