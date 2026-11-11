#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Native Qt client + actual distribution service, with isolated test credentials."""
import fcntl
import base64
import hashlib
import http.client
import struct
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import ssl
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import elo_content as content
import elo_server

CLIENT = Path(os.environ.get('ELO_CLIENT_BIN', ROOT / 'build/client-fedora/elo-client')).resolve()


class DistributionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not CLIENT.is_file():
            raise RuntimeError('Build native Qt client first (scripts/run-client.sh)')
        cls.cert_temp = tempfile.TemporaryDirectory()
        cls.cert_dir = Path(cls.cert_temp.name)
        cls.cert = cls.cert_dir / 'cert.pem'
        cls.key = cls.cert_dir / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost',
                        '-keyout', str(cls.key), '-out', str(cls.cert)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @classmethod
    def tearDownClass(cls):
        cls.cert_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bundle = self.base / 'publication'
        self.cache = self.base / 'cache'
        self.token_file = self.base / 'terminal.secret'
        self.token = elo_server.terminal_token(self.token_file, create=True)
        self.write_bundle()
        self.children = []
        self.services = []
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for child, log in self.children:
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=5)
            log.close()
        for service in self.services:
            service.shutdown()
            service.server_close()

    def write_bundle(self):
        files = {
            'catalog/atoms/one.json': {'schema_version': '0.2', 'content_id': 'one'},
            'catalog/variants/text.json': {'variant_id': 'text', 'content_id': 'one', 'interaction': 'none',
                                          'presentation': {'title': 'Do servidor ELO', 'text': 'Disponível sem rede.'}}}
        digest = hashlib.sha256()
        for name, value in sorted(files.items()):
            path = self.bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            data = content.encoded(value)
            path.write_bytes(data)
            digest.update(name.encode())
            digest.update(data)
        (self.bundle / 'manifest.json').write_bytes(content.encoded({
            'schema_version': '0.2', 'bundle_id': 'test-application', 'version': '1.0.0',
            'title': 'Aplicação de teste', 'atom_ids': ['one'], 'content_hash': 'sha256:' + digest.hexdigest()}))

    def listen(self, service, tls=False):
        if tls:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(self.cert, self.key)
            service.socket = context.wrap_socket(service.socket, server_side=True)
        self.services.append(service)
        thread = threading.Thread(target=service.serve_forever, daemon=True)
        thread.start()
        return service.server_port

    def actual_server(self, tls=False):
        return self.listen(elo_server.server(self.bundle, ['text'], self.token), tls)

    def raw_server(self, body, status=200, headers=None, declared_size=None):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body) if declared_size is None else declared_size))
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                self.close_connection = True
        return self.listen(ThreadingHTTPServer(('127.0.0.1', 0), Handler))

    def launch(self, port, tls=False, ca=True, host=None, extra=None):
        index = len(self.children)
        health = self.base / f'health-{index}'
        log_path = self.base / f'log-{index}'
        log = log_path.open('w')
        host = host or ('localhost' if tls else '127.0.0.1')
        args = [str(CLIENT), '--content-dir', str(self.cache), '--server',
                f'{"https" if tls else "http"}://{host}:{port}/v1/presentation',
                '--token-file', str(self.token_file), '--health-file', str(health), '--health-token', 'distribution-test']
        if not tls:
            args += ['--allow-loopback-http']
        elif ca:
            args += ['--ca-file', str(self.cert)]
        args += extra or []
        child = subprocess.Popen(args, stdout=log, stderr=log,
                                 env=dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', QT_FORCE_STDERR_LOGGING='1'))
        self.children.append((child, log))
        return child, health, log_path

    def wait(self, predicate, timeout=12):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.05)
        self.fail('Timed out waiting for distribution state: ' + '\n'.join(p.read_text()[-1200:] for p in self.base.glob('log-*')))

    def frame(self, health):
        if not health.exists():
            return []
        return health.read_text().split()

    def seeded_cache(self):
        data = content.encoded({'schema': 1, 'id': 'cached', 'name': 'Cache anterior', 'version': '1',
                                'pages': [{'title': 'Anterior', 'body': 'Preservado.'}]})
        path = self.base / 'seed.json'
        path.write_bytes(data)
        content.activate(self.cache, path, len(data), hashlib.sha256(data).hexdigest())
        return (self.cache / 'active.json').read_bytes()

    def test_http_download_render_and_restart_without_server(self):
        port = self.actual_server()
        child, health, log = self.launch(port)
        self.wait(lambda: 'conteúdo recebido (HTTP)' in log.read_text())
        self.wait(lambda: len(self.frame(health)) == 8 and self.frame(health)[5] == 'READY_LOCAL')
        active = content.read_active(self.cache)
        self.assertEqual(active['id'], 'test-application')
        parts = [active['id'], active['version'], active['pages'][0]['title'], active['pages'][0]['body']]
        expected = hashlib.sha256(b''.join(x.encode() + b'\0' for x in parts)).hexdigest()
        self.wait(lambda: self.frame(health)[7] == expected)
        child.terminate()
        child.wait(timeout=5)
        service = self.services.pop()
        service.shutdown()
        service.server_close()
        child, health, log = self.launch(port)
        self.wait(lambda: 'Servidor indisponível' in log.read_text())
        self.wait(lambda: len(self.frame(health)) == 8 and self.frame(health)[7] == expected)
        self.assertIn(self.frame(health)[5], ('READY_LOCAL', 'DEGRADED_OFFLINE'))

    def test_recovers_when_server_appears_after_offline_boot(self):
        self.seeded_cache()
        with socket.socket() as reserved:
            reserved.bind(('127.0.0.1', 0))
            port = reserved.getsockname()[1]
        child, health, log = self.launch(port)
        self.wait(lambda: 'fetch_failed' in log.read_text())
        self.wait(lambda: len(self.frame(health)) == 8 and self.frame(health)[5] == 'READY_LOCAL')
        service = elo_server.server(self.bundle, ['text'], self.token, port=port)
        self.listen(service)
        self.wait(lambda: 'conteúdo recebido (HTTP)' in log.read_text(), timeout=20)
        self.wait(lambda: service.receipts.record and service.receipts.record.get('display'), timeout=20)
        self.assertIsNone(child.poll())
        self.assertEqual(content.read_active(self.cache)['id'], 'test-application')

    def test_reports_exact_content_after_a_rendered_frame(self):
        port = self.actual_server()
        child, health, log = self.launch(port)
        receipt = self.services[-1].receipts
        self.wait(lambda: receipt.record and bool(receipt.record['presented_sha256']))
        active = (self.cache / 'active.json')
        self.wait(lambda: active.exists())
        digest = json.loads(active.read_text())['bundle']
        self.wait(lambda: receipt.record['received_sha256'] == digest and receipt.record['presented_sha256'] == digest)
        self.assertEqual(receipt.status(digest)['state'], 'presented')
        self.assertEqual(receipt.record['schema'], 2)
        self.assertEqual(receipt.record['display']['title'], 'Do servidor ELO')
        self.assertEqual(receipt.record['display']['page'], 1)

    def test_two_native_terminals_report_separate_presentations(self):
        from elo_panel import Panel
        panel = Panel(self.bundle, ['text'], b'a' * 43, self.base / 'state/selection.json', ROOT / 'web/distribution')
        first = panel.terminals.add({'name': 'Totem A'})
        second = panel.terminals.add({'name': 'Totem B'})
        port = self.listen(elo_server.server(self.bundle, ['text'], self.token, panel=panel), tls=True)
        for index, entry in enumerate((first, second)):
            self.token_file = self.base / f'terminal-{index}.token'
            self.token_file.write_text(entry['token']); self.token_file.chmod(0o600)
            self.cache = self.base / f'cache-{index}'
            self.launch(port, tls=True)
        one = panel.terminals.receipt(first['id'])
        two = panel.terminals.receipt(second['id'])
        self.wait(lambda: one.record and two.record and one.record.get('display') and two.record.get('display'))
        self.assertNotEqual(one.record['session'], two.record['session'])
        self.assertEqual(one.record['display']['title'], 'Do servidor ELO')
        self.assertEqual(two.record['display']['title'], 'Do servidor ELO')
        self.assertIsNone(panel.receipts.record)

    def test_automatic_page_change_updates_confirmed_display(self):
        from elo_panel import Panel
        path = self.bundle / 'catalog/variants/text.json'
        first = json.loads(path.read_text())
        second = first | {'variant_id': 'text-2', 'presentation': {'title': 'Segunda página real', 'text': 'Exposição automática.'}}
        path.write_bytes(content.encoded([first, second]))
        digest = hashlib.sha256()
        for path in sorted(self.bundle.rglob('*')):
            if path.is_file() and path.name != 'manifest.json':
                digest.update(path.relative_to(self.bundle).as_posix().encode()); digest.update(path.read_bytes())
        path = self.bundle / 'manifest.json'; manifest = json.loads(path.read_text())
        manifest['content_hash'] = 'sha256:' + digest.hexdigest(); path.write_bytes(content.encoded(manifest))
        panel = Panel(self.bundle, ['text'], b'a' * 43, self.base / 'state/selection.json', ROOT / 'web/distribution')
        panel.select({'variants': ['text', 'text-2'], 'expected_hash': manifest['content_hash'], 'exposure_seconds': 5})
        port = self.listen(elo_server.server(self.bundle, ['text'], self.token, panel=panel), tls=True)
        self.launch(port, tls=True)
        self.wait(lambda: panel.receipts.record and panel.receipts.record.get('display', {}).get('page') == 1)
        publication = panel.receipts.record['presented_sha256']
        self.wait(lambda: panel.receipts.record.get('display', {}).get('page') == 2)
        self.assertEqual(panel.receipts.record['display']['title'], 'Segunda página real')
        self.assertEqual(panel.receipts.record['presented_sha256'], publication)

    def test_downloaded_update_does_not_claim_presentation(self):
        self.seeded_cache()
        previous = json.loads((self.cache / 'active.json').read_text())['bundle']
        port = self.actual_server()
        child, health, log = self.launch(port)
        receipt = self.services[-1].receipts
        self.wait(lambda: 'conteúdo recebido (HTTP)' in log.read_text())
        digest = json.loads((self.cache / 'active.json').read_text())['bundle']
        self.assertNotEqual(previous, digest)
        self.wait(lambda: receipt.record and receipt.record['received_sha256'] == digest)
        self.assertEqual(receipt.record['presented_sha256'], previous)
        self.assertEqual(receipt.status(digest)['state'], 'received')

    def test_image_download_requires_capability_and_survives_offline_restart(self):
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
        raw = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
               + chunk(b'IDAT', zlib.compress(b'\x00\xea\x27\x39')) + chunk(b'IEND', b''))
        path = self.bundle / 'assets/test.png'; path.parent.mkdir(parents=True); path.write_bytes(raw)
        path = self.bundle / 'catalog/variants/text.json'
        variant = json.loads(path.read_text()); variant['presentation']['media'] = ['assets/test.png']
        path.write_bytes(content.encoded(variant))
        digest = hashlib.sha256()
        for path in sorted(self.bundle.rglob('*')):
            if path.is_file() and path.name != 'manifest.json':
                digest.update(path.relative_to(self.bundle).as_posix().encode()); digest.update(path.read_bytes())
        path = self.bundle / 'manifest.json'; manifest = json.loads(path.read_text())
        manifest['content_hash'] = 'sha256:' + digest.hexdigest(); path.write_bytes(content.encoded(manifest))
        port = self.actual_server(tls=True)
        connection = http.client.HTTPSConnection('localhost', port, context=ssl.create_default_context(cafile=str(self.cert)))
        connection.request('GET', '/v1/presentation', headers={'Authorization': 'Bearer ' + self.token.decode()})
        response = connection.getresponse(); self.assertEqual(response.status, 409); response.read(); connection.close()
        child, health, log = self.launch(port, tls=True)
        receipt = self.services[-1].receipts
        self.wait(lambda: receipt.record and receipt.record['presented_sha256'])
        active = content.read_active(self.cache)
        self.assertEqual(active['version'], '2')
        self.assertEqual(active['pages'][0]['image']['sha256'], hashlib.sha256(raw).hexdigest())
        previous_frame = self.frame(health)[7]
        child.terminate(); child.wait(timeout=5)
        service = self.services.pop(); service.shutdown(); service.server_close()
        child, health, log = self.launch(port, tls=True)
        self.wait(lambda: len(self.frame(health)) == 8 and self.frame(health)[7] == previous_frame)
        self.assertIn(self.frame(health)[5], ('READY_LOCAL', 'DEGRADED_OFFLINE'))

    @unittest.skipUnless(os.environ.get('ELO_AV_TEST') == '1', 'Requires audiovisual-enabled client and ffmpeg')
    def test_audiovisual_download_and_offline_restart(self):
        import wave
        for kind in ('audio', 'video'):
            with self.subTest(kind=kind):
                self.cache = self.base / ('cache-' + kind)
                assets = self.bundle / 'assets'; assets.mkdir(exist_ok=True)
                asset = assets / ('sample.wav' if kind == 'audio' else 'sample.webm')
                if kind == 'audio':
                    with wave.open(str(asset), 'wb') as output:
                        output.setnchannels(1); output.setsampwidth(2); output.setframerate(16000)
                        output.writeframes(b'\0\0' * 32000)
                else:
                    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=320x180:r=10:d=2',
                                    '-c:v', 'libvpx', '-an', '-y', str(asset)], check=True)
                path = self.bundle / 'catalog/variants/text.json'
                variant = json.loads(path.read_text()); variant['presentation']['media'] = ['assets/' + asset.name]
                path.write_bytes(content.encoded(variant))
                digest = hashlib.sha256()
                for file in sorted(self.bundle.rglob('*')):
                    if file.is_file() and file.name != 'manifest.json':
                        digest.update(file.relative_to(self.bundle).as_posix().encode()); digest.update(file.read_bytes())
                path = self.bundle / 'manifest.json'; manifest = json.loads(path.read_text())
                manifest['content_hash'] = 'sha256:' + digest.hexdigest(); path.write_bytes(content.encoded(manifest))
                port = self.actual_server(tls=True)
                connection = http.client.HTTPSConnection('localhost', port, context=ssl.create_default_context(cafile=str(self.cert)))
                connection.request('GET', '/v1/presentation', headers={'Authorization': 'Bearer ' + self.token.decode(),
                    'X-ELO-Capabilities': 'text-v1,image-v2,reveal-v3,autoplay-v4'})
                response = connection.getresponse(); self.assertEqual(response.status, 409); response.read(); connection.close()
                child, health, log = self.launch(port, tls=True)
                receipt = self.services[-1].receipts
                self.wait(lambda: receipt.record and receipt.record['presented_sha256'])
                active = content.read_active(self.cache); self.assertEqual(active['version'], '5')
                self.assertEqual(active['pages'][0]['media']['kind'], kind)
                previous = self.frame(health)[7]
                child.terminate(); child.wait(timeout=5)
                service = self.services.pop(); service.shutdown(); service.server_close()
                child, health, log = self.launch(port, tls=True)
                self.wait(lambda: len(self.frame(health)) == 8 and self.frame(health)[7] == previous)
                self.assertIn(self.frame(health)[5], ('READY_LOCAL', 'DEGRADED_OFFLINE'))
                child.terminate(); child.wait(timeout=5)

    def test_reveal_capability_and_concealed_offline_restart(self):
        path = self.bundle / 'catalog/variants/text.json'
        variant = json.loads(path.read_text()); variant['interaction'] = 'reveal'
        path.write_bytes(content.encoded(variant))
        digest = hashlib.sha256()
        for path in sorted(self.bundle.rglob('*')):
            if path.is_file() and path.name != 'manifest.json':
                digest.update(path.relative_to(self.bundle).as_posix().encode()); digest.update(path.read_bytes())
        path = self.bundle / 'manifest.json'; manifest = json.loads(path.read_text())
        manifest['content_hash'] = 'sha256:' + digest.hexdigest(); path.write_bytes(content.encoded(manifest))
        port = self.actual_server(tls=True)
        connection = http.client.HTTPSConnection('localhost', port, context=ssl.create_default_context(cafile=str(self.cert)))
        connection.request('GET', '/v1/presentation', headers={'Authorization': 'Bearer ' + self.token.decode(),
            'X-ELO-Capabilities': 'text-v1,image-v2'})
        response = connection.getresponse(); self.assertEqual(response.status, 409); response.read(); connection.close()
        child, health, log = self.launch(port, tls=True)
        receipt = self.services[-1].receipts
        self.wait(lambda: receipt.record and receipt.record['presented_sha256'])
        active = content.read_active(self.cache)
        self.assertEqual(active['version'], '3')
        self.assertEqual(active['pages'][0]['interaction'], 'reveal')
        parts = [active['id'], '3', active['pages'][0]['title'], 'Toque em Revelar para descobrir.']
        expected = hashlib.sha256(b''.join(x.encode() + b'\0' for x in parts)).hexdigest()
        self.wait(lambda: len(self.frame(health)) == 8 and self.frame(health)[7] == expected)
        child.terminate(); child.wait(timeout=5)
        service = self.services.pop(); service.shutdown(); service.server_close()
        child, health, log = self.launch(port, tls=True)
        self.wait(lambda: len(self.frame(health)) == 8 and self.frame(health)[7] == expected)

    def test_automatic_playback_enters_without_mouse_and_loops_offline(self):
        from elo_panel import Panel
        panel = Panel(self.bundle, ['text'], b'a' * 43, self.base / 'selection.json', ROOT / 'web/distribution')
        manifest = json.loads((self.bundle / 'manifest.json').read_text())
        panel.select({'variants': ['text'], 'expected_hash': manifest['content_hash'], 'exposure_seconds': 5})
        port = self.listen(elo_server.server(self.bundle, ['text'], self.token, panel=panel), tls=True)
        connection = http.client.HTTPSConnection('localhost', port, context=ssl.create_default_context(cafile=str(self.cert)))
        connection.request('GET', '/v1/presentation', headers={'Authorization': 'Bearer ' + self.token.decode(),
            'X-ELO-Capabilities': 'text-v1,image-v2,reveal-v3'})
        response = connection.getresponse(); self.assertEqual(response.status, 409); response.read(); connection.close()
        self.seeded_cache() # Existing manual session must switch without a local reset.
        child, health, log = self.launch(port, tls=True)
        self.wait(lambda: 'fixture=test-application' in log.read_text())
        self.assertEqual(content.read_active(self.cache)['exposure_seconds'], 5)
        service = self.services.pop(); service.shutdown(); service.server_close()
        # Single-page sequence stays healthy through multiple unattended cycles offline.
        self.wait(lambda: len(self.frame(health)) == 8)
        sequence = int(self.frame(health)[4])
        time.sleep(6)
        self.assertIsNone(child.poll())
        self.assertGreater(int(self.frame(health)[4]), sequence)
        self.assertEqual(self.frame(health)[6], '1')

    def test_invalid_image_bytes_preserve_previous_cache(self):
        previous = self.seeded_cache()
        raw = b'\x89PNG\r\n\x1a\ninvalid'
        document = {'schema': 1, 'id': 'bad-image', 'name': 'Imagem inválida', 'version': '2',
                    'pages': [{'title': 'Teste', 'body': 'Não substituir cache.', 'image': {
                        'mime': 'image/png', 'base64': base64.b64encode(raw).decode(),
                        'sha256': hashlib.sha256(raw).hexdigest(), 'alt': 'Teste'}}]}
        payload = content.encoded(document)
        value = json.loads(elo_server.envelope(self.bundle, ['text']))
        value.update(presentation=payload.decode(), size=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        port = self.raw_server(content.encoded(value))
        child, health, log = self.launch(port)
        self.wait(lambda: 'Servidor indisponível' in log.read_text())
        self.assertEqual((self.cache / 'active.json').read_bytes(), previous)

    def test_headless_https_probe_reports_failure_without_credential_leak(self):
        probe = CLIENT.parent / 'elo-network-probe'
        self.assertTrue(probe.is_file())
        port = self.actual_server(tls=True)
        args = [str(probe), '--server', f'https://localhost:{port}/v1/presentation',
                '--token-file', str(self.token_file), '--ca-file', str(self.cert)]
        result = subprocess.run(args, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('HTTP: 200', result.stdout)
        self.assertNotIn(self.token.decode(), result.stdout + result.stderr)
        self.token_file.write_text('x' * 43)
        result = subprocess.run(args, capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('HTTP: 401', result.stdout)
        self.assertNotIn('x' * 43, result.stdout + result.stderr)
        args[2] = f'https://127.0.0.1:{port}/v1/presentation'
        result = subprocess.run(args, capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('TLS:', result.stdout)

    def test_https_with_explicit_trust(self):
        port = self.actual_server(tls=True)
        child, health, log = self.launch(port, tls=True)
        self.wait(lambda: 'conteúdo recebido (HTTPS)' in log.read_text())
        self.assertEqual(content.read_active(self.cache)['id'], 'test-application')
        self.assertNotIn(self.token.decode(), log.read_text())

    def test_untrusted_certificate_and_wrong_hostname_preserve_cache(self):
        previous = self.seeded_cache()
        port = self.actual_server(tls=True)
        for options in ({'ca': False}, {'host': '127.0.0.1'}):
            child, health, log = self.launch(port, tls=True, **options)
            self.wait(lambda: 'Servidor indisponível' in log.read_text())
            self.assertEqual((self.cache / 'active.json').read_bytes(), previous)
            child.terminate()
            child.wait(timeout=5)

    def test_unauthorized_terminal_preserves_cache(self):
        previous = self.seeded_cache()
        port = self.actual_server()
        self.token_file.write_text('x' * 43 + '\n')
        child, health, log = self.launch(port)
        self.wait(lambda: 'Servidor indisponível' in log.read_text())
        self.assertEqual((self.cache / 'active.json').read_bytes(), previous)
        self.assertNotIn('x' * 43, log.read_text())

    def test_bad_responses_and_redirect_preserve_cache(self):
        previous = self.seeded_cache()
        valid = json.loads(elo_server.envelope(self.bundle, ['text']))
        invalid = dict(valid, sha256='0' * 64)
        unsupported = dict(valid, schema=99)
        malformed = dict(valid, presentation='{}', size=2, sha256=hashlib.sha256(b'{}').hexdigest())
        # Include structurally invalid but correctly hashed content.
        for body, status, headers in ((content.encoded(invalid), 200, {}),
                                      (content.encoded(unsupported), 200, {}),
                                      (content.encoded(malformed), 200, {}),
                                      (b'{', 200, {}),
                                      (b'x' * (2 * 1024 * 1024 + 1), 200, {}),
                                      (b'', 302, {'Location': '/v1/presentation'})):
            port = self.raw_server(body, status, headers)
            child, health, log = self.launch(port)
            self.wait(lambda: 'Servidor indisponível' in log.read_text())
            self.assertEqual((self.cache / 'active.json').read_bytes(), previous)
            child.terminate()
            child.wait(timeout=5)

    def test_tampered_publication_is_not_served(self):
        previous = self.seeded_cache()
        port = self.actual_server()
        (self.bundle / 'catalog/atoms/one.json').write_text('{}')
        child, health, log = self.launch(port)
        self.wait(lambda: 'Servidor indisponível' in log.read_text())
        self.assertEqual((self.cache / 'active.json').read_bytes(), previous)

    def test_interrupted_download_preserves_cache(self):
        previous = self.seeded_cache()
        body = elo_server.envelope(self.bundle, ['text'])
        port = self.raw_server(body[:len(body) // 2], declared_size=len(body))
        child, health, log = self.launch(port)
        self.wait(lambda: 'Servidor indisponível' in log.read_text())
        self.assertEqual((self.cache / 'active.json').read_bytes(), previous)

    def test_missing_credential_preserves_offline_presentation(self):
        previous = self.seeded_cache()
        self.token_file.unlink()
        child, health, log = self.launch(9)
        self.wait(lambda: 'Servidor indisponível' in log.read_text())
        self.wait(lambda: len(self.frame(health)) == 8 and self.frame(health)[5] == 'READY_LOCAL')
        self.assertEqual((self.cache / 'active.json').read_bytes(), previous)

    def test_busy_activation_lock_preserves_cache_then_retries(self):
        previous = self.seeded_cache()
        port = self.actual_server()
        with (self.cache / '.activation.lock').open('r+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            child, health, log = self.launch(port)
            self.wait(lambda: 'Servidor indisponível' in log.read_text())
            self.assertEqual((self.cache / 'active.json').read_bytes(), previous)
        self.wait(lambda: 'conteúdo recebido (HTTP)' in log.read_text(), timeout=8)
        self.assertEqual(content.read_active(self.cache)['id'], 'test-application')
        self.assertIn('Novo conteúdo disponível', log.read_text())
        # The displayed session stays on its previous page until Recomeçar.
        old_digest = hashlib.sha256(b'cached\x001\x00Anterior\x00Preservado.\x00').hexdigest()
        self.wait(lambda: len(self.frame(health)) == 8 and self.frame(health)[7] == old_digest)

    def test_http_requires_explicit_flag(self):
        result = subprocess.run([str(CLIENT), '--content-dir', str(self.cache), '--server',
                                 'http://127.0.0.1:9/v1/presentation', '--token-file', str(self.token_file)],
                                env=dict(os.environ, QT_QPA_PLATFORM='offscreen'), capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.cache / 'active.json').exists())


if __name__ == '__main__':
    unittest.main()
