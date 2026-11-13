#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Read-only ELO text distribution service, protocol 1 with individual terminal credentials."""
import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
import secrets
import ssl
import stat
import sqlite3

from elo_content import encoded
from elo_import import project
from elo_receipts import Receipts
from elo_ingest import IngestError


def terminal_token(path, create=False):
    path = Path(path)
    if create and not path.exists():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(secrets.token_urlsafe(32) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise ValueError('Token file must be a private regular file (0600)')
        token = stream.read(257).strip()
    if not re.fullmatch(rb'[A-Za-z0-9_-]{32,128}', token):
        raise ValueError('Invalid terminal token')
    return token


def envelope(bundle, variants, exposure_seconds=0):
    data, source = project(bundle, variants)
    if exposure_seconds:
        from elo_content import decode, fixture
        value = decode(data)
        value.update(version="5" if value["version"] == "5" else "4", exposure_seconds=exposure_seconds)
        data = encoded(value)
        fixture(data)
    return encoded({'schema': 1, 'sha256': hashlib.sha256(data).hexdigest(),
                    'size': len(data), 'presentation': data.decode('utf-8'),
                    'source': {'bundle_id': source['bundle_id'], 'version': source['version'],
                               'content_hash': source['content_hash'], 'variants': variants}})


def server(bundle, variants, token, host='127.0.0.1', port=0, panel=None, ingest=None):
    if ingest and (hmac.compare_digest(ingest.token, token)
                   or (panel and hmac.compare_digest(ingest.token, panel.token))):
        raise ValueError('Ingest, terminal and admin credentials must be distinct')
    receipts = panel.receipts if panel else Receipts()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.connection = self.request
            if getattr(self.server, 'ssl_context', None):
                self.connection.settimeout(10)
                try:
                    self.connection = self.server.ssl_context.wrap_socket(self.connection, server_side=True)
                except (ssl.SSLError, TimeoutError, OSError):
                    import io
                    self.rfile = io.BytesIO()
                    self.wfile = io.BytesIO()
                    self.close_connection = True
                    return
                self.request = self.connection
            super().setup()

        def log_message(self, format, *args):
            pass  # Never log request headers, token, query or content.

        def respond(self, status, body, content_type='application/json; charset=utf-8', extra_headers=()):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; font-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            for name, value in extra_headers:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def authorized(self, credential):
            auth = self.headers.get_all('Authorization', [])
            return len(auth) == 1 and hmac.compare_digest(auth[0].encode('utf-8'), b'Bearer ' + credential)

        def terminal_identity(self):
            if self.authorized(token): return 'local'
            values = self.headers.get_all('Authorization', [])
            if panel and len(values) == 1 and values[0].startswith('Bearer '):
                return panel.terminals.authenticate(values[0][7:].encode('utf-8'))
            return None

        def admin_request(self, method):
            if not panel or not self.authorized(panel.token):
                self.respond(401, b'{"error":"unauthorized"}')
                return
            scheme = 'https' if (getattr(self.server, 'ssl_context', None) or isinstance(self.connection, ssl.SSLSocket)) else 'http'
            allowed = {f'{scheme}://localhost:{self.server.server_port}', f'{scheme}://127.0.0.1:{self.server.server_port}', f'{scheme}://{self.headers.get("Host", "")}'}
            if self.headers.get('Origin') and self.headers['Origin'] not in allowed:
                self.respond(403, b'{"error":"origin_rejected"}')
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if self.headers.get('Transfer-Encoding') or size < 0 or size > 32 * 1024 * 1024:
                    self.respond(413, b'{"error":"request_too_large"}')
                    return
                body = self.rfile.read(size)
                if len(body) != size:
                    raise ValueError('Requisição incompleta')
                if self.path == '/manage/status' and method == 'GET':
                    self.respond(200, encoded(panel.status()), extra_headers=[('Set-Cookie', 'elo_media=' + panel.media_cookie() + '; Path=/studio/assets/; HttpOnly; SameSite=Strict' + ('; Secure' if scheme == 'https' else ''))])
                elif self.path == '/manage/ingest' and method == 'GET':
                    self.respond(200, encoded(ingest.summaries()) if ingest else b'{"enabled":false}')
                elif self.path == '/manage/ingest/import' and method == 'POST':
                    from elo_content import decode
                    if not ingest:
                        raise IngestError(503, 'ingest_disabled')
                    if size > 12 * 1024 * 1024:
                        raise IngestError(413, 'request_too_large')
                    self.respond(200, encoded(ingest.import_package(decode(body))))
                elif re.fullmatch(r'/manage/ingest/(sub_[0-9a-f]{32})/audio', self.path) and method == 'GET':
                    if not ingest:
                        raise IngestError(503, 'ingest_disabled')
                    self.respond(200, ingest.audio(self.path.split('/')[3]), 'audio/wav')
                elif self.path == '/manage/delivery' and method == 'GET':
                    self.respond(200, encoded(panel.delivery()))
                elif self.path == '/manage/terminals' and method == 'GET':
                    self.respond(200, encoded(panel.terminal_status()))
                elif self.path == '/manage/terminals' and method == 'POST':
                    from elo_content import decode
                    if size > 1024: raise ValueError('Terminal request too large')
                    self.respond(201, encoded(panel.terminals.add(decode(body))))
                elif re.fullmatch(r'/manage/terminals/[0-9a-f]{16}/power', self.path) and method == 'POST':
                    from elo_content import decode
                    if size > 1024: raise ValueError('Comando muito grande')
                    self.respond(202, encoded(panel.terminals.power(self.path.split('/')[3], decode(body))))
                elif self.path.startswith('/manage/terminals/') and self.path.endswith('/revoke') and method == 'POST':
                    self.respond(200, encoded(panel.terminals.revoke(self.path.split('/')[3])))
                elif self.path == '/manage/logout' and method == 'POST':
                    self.respond(200, b'{}', extra_headers=[('Set-Cookie', 'elo_media=; Max-Age=0; Path=/studio/assets/; HttpOnly; SameSite=Strict')])
                elif self.path == '/manage/selection' and method == 'POST':
                    from elo_content import decode
                    if size > 16384:
                        raise ValueError('Seleção muito grande')
                    self.respond(200, encoded(panel.select(decode(body))))
                elif self.path.startswith('/api/'):
                    status, mime, data = panel.proxy(method, self.path, body, self.headers.get('Content-Type', 'application/json'))
                    self.respond(status, data, mime)
                else:
                    self.respond(404, b'{"error":"not_found"}')
            except IngestError as error:
                self.respond(error.status, encoded({'error': error.code}))
            except ValueError as error:
                import traceback; traceback.print_exc()
                self.respond(400, encoded({'error': str(error) if self.path.endswith('/power') else 'Operação recusada. Confira publicação, seleção e disponibilidade do Estúdio.'}))
            except (OSError, UnicodeError):
                import traceback; traceback.print_exc()
                self.respond(400, encoded({'error': 'Operação recusada. Confira publicação, seleção e disponibilidade do Estúdio.'}))
            except Exception:
                import traceback; traceback.print_exc()
                self.respond(502, b'{"error":"editorial_service_unavailable"}')

        def ingest_request(self, method):
            from elo_ingest import IngestError
            from elo_consumable import MAX_MANIFEST
            from elo_content import decode
            if not ingest:
                self.respond(404, b'{"error":"ingest_disabled"}')
                return
            if not self.authorized(ingest.token):
                self.respond(401, b'{"error":"unauthorized"}')
                return
            # Machine-to-machine only; browser sessions must use editorial routes.
            if self.headers.get_all('Origin'):
                self.respond(403, b'{"error":"origin_rejected"}')
                return
            try:
                lengths = self.headers.get_all('Content-Length', [])
                if not lengths and method == 'GET':
                    lengths = ['0']
                if self.headers.get_all('Transfer-Encoding') or len(lengths) != 1 or not re.fullmatch(r'[0-9]{1,10}', lengths[0]):
                    raise IngestError(400, 'invalid_content_length')
                size = int(lengths[0])
                base = '/v1/ingest/submissions'
                limit = 0
                asset = None
                upload = re.fullmatch(base + r'/(sub_[0-9a-f]{32})/assets/([A-Za-z0-9][A-Za-z0-9_-]{0,127})', self.path)
                item = re.fullmatch(base + r'/(sub_[0-9a-f]{32})(/commit)?', self.path)
                if self.path == base and method == 'POST':
                    limit = MAX_MANIFEST
                    if self.headers.get_all('Content-Type') != ['application/json']:
                        raise IngestError(415, 'unsupported_content_type')
                    keys = self.headers.get_all('Idempotency-Key', [])
                    if len(keys) != 1:
                        raise IngestError(400, 'invalid_idempotency_key')
                elif upload and method == 'PUT':
                    asset = ingest.asset_spec(*upload.groups())
                    limit = asset['size_bytes']
                    if self.headers.get_all('Content-Type') != [asset['mime']]:
                        raise IngestError(415, 'unsupported_content_type')
                    if size != limit:
                        raise IngestError(422, 'asset_size_mismatch')
                elif not (item and ((method == 'GET' and not item[2])
                                            or (method == 'POST' and item[2] == '/commit'))):
                    raise IngestError(404, 'not_found')
                if size > limit:
                    raise IngestError(413, 'request_too_large')
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise IngestError(400, 'incomplete_request')
                status = 200
                if self.path == base:
                    try:
                        value = decode(raw)
                    except (ValueError, UnicodeError):
                        raise IngestError(422, 'invalid_manifest') from None
                    receipt, created = ingest.create(value, keys[0])
                    status = 201 if created else 200
                elif asset is not None:
                    receipt = ingest.upload(*upload.groups(), raw)
                elif item[2]:
                    receipt = ingest.commit(item[1])
                else:
                    receipt = ingest.get(item[1])
                self.respond(status, encoded(receipt))
            except IngestError as error:
                self.respond(error.status, encoded({'error': error.code}))
            except (ValueError, UnicodeError):
                self.respond(422, b'{"error":"invalid_package"}')
            except (OSError, sqlite3.Error):
                self.respond(503, b'{"error":"intake_unavailable"}')

        def do_POST(self):
            if self.path in ('/v1/control/poll', '/v1/control/ack'):
                identity = self.terminal_identity()
                if not panel or not identity or identity == 'local':
                    self.respond(401, b'{"error":"unauthorized"}')
                    return
                try:
                    from elo_content import decode
                    size = int(self.headers.get('Content-Length', '0'))
                    if self.headers.get('Transfer-Encoding') or not 1 <= size <= 1024:
                        raise ValueError('Invalid control request size')
                    data = self.rfile.read(size)
                    if len(data) != size: raise ValueError('Incomplete control request')
                    control = panel.terminals.control
                    result = control.poll(identity, decode(data)) if self.path.endswith('/poll') else control.acknowledge(identity, decode(data))
                    self.respond(200, encoded(result))
                except (ValueError, OSError, UnicodeError):
                    self.respond(400, b'{"error":"control_rejected"}')
                return
            if self.path.startswith('/v1/ingest/'):
                self.ingest_request('POST')
                return
            if self.path == '/v1/receipt':
                identity = self.terminal_identity()
                if not identity:
                    self.respond(401, b'{"error":"unauthorized"}')
                    return
                try:
                    from elo_content import decode
                    size = int(self.headers.get('Content-Length', '0'))
                    if self.headers.get('Transfer-Encoding') or not 1 <= size <= 2048:
                        raise ValueError('Invalid receipt size')
                    (panel.terminals.receipt(identity) if panel else receipts).accept(decode(self.rfile.read(size)))
                    self.respond(200, b'{"accepted":true}')
                except (ValueError, OSError, UnicodeError):
                    self.respond(400, b'{"error":"receipt_rejected"}')
                return
            self.admin_request('POST')

        def do_PUT(self):
            if self.path.startswith('/v1/ingest/'):
                self.ingest_request('PUT')
                return
            self.admin_request('PUT')

        def do_DELETE(self):
            if self.path.startswith('/v1/ingest/'):
                self.ingest_request('DELETE')
                return
            self.admin_request('DELETE')

        def do_GET(self):
            if self.path.startswith('/v1/ingest/'):
                self.ingest_request('GET')
                return
            assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/elo.svg': ('elo.svg', 'image/svg+xml'),
                      '/elo-os.svg': ('elo-os.svg', 'image/svg+xml'),
                      '/elo-os-client.svg': ('elo-os-client.svg', 'image/svg+xml'),
                      '/panel.css': ('panel.css', 'text/css; charset=utf-8'),
                      '/panel.js': ('panel.js', 'text/javascript; charset=utf-8'),
                      '/studio/': ('studio/index.html', 'text/html; charset=utf-8'),
                      '/studio/app.css': ('studio/app.css', 'text/css; charset=utf-8'),
                      '/studio/theme.css': ('studio-morfo.css', 'text/css; charset=utf-8'),
                      '/studio/app.js': ('studio/app.js', 'text/javascript; charset=utf-8')}
            static_path = self.path.split('?', 1)[0]
            if panel and static_path in assets:
                filename, mime = assets[static_path]
                self.respond(200, (panel.web_root / filename).read_bytes(), mime)
                return
            if panel and self.path.startswith('/studio/assets/'):
                if not panel.media_authorized(self.headers.get('Cookie')):
                    self.respond(401, b'{"error":"unauthorized"}')
                    return
                try:
                    status, mime, data = panel.proxy('GET', self.path[len('/studio'):], b'', 'application/json')
                    self.respond(status, data, mime)
                except (OSError, ValueError):
                    self.respond(404, b'{"error":"media_unavailable"}')
                return
            if self.path.startswith(('/manage/', '/api/')):
                self.admin_request('GET')
                return
            if not self.terminal_identity():
                self.respond(401, b'{"error":"unauthorized"}')
                return
            if self.path != '/v1/presentation':
                self.respond(404, b'{"error":"not_found"}')
                return
            try:
                body = panel.envelope() if panel else envelope(bundle, variants)
                from elo_content import decode
                presentation = decode(decode(body)['presentation'].encode())
                required = set()
                if any('image' in page for page in presentation['pages']): required.add('image-v2')
                if any(page.get('interaction') == 'reveal' for page in presentation['pages']): required.add('reveal-v3')
                if presentation.get('exposure_seconds'): required.add('autoplay-v4')
                if any('media' in page for page in presentation['pages']): required.add('audiovisual-v5')
                if not required.issubset(self.headers.get('X-ELO-Capabilities', '').split(',')):
                    self.respond(409, b'{"error":"content_capability_required"}')
                    return
            except (OSError, ValueError, UnicodeError, KeyError):
                self.respond(503, b'{"error":"publication_unavailable"}')
                return
            self.respond(200, body)

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        ssl_context = None

        def handle_error(self, request, client_address):
            pass

    instance = Server((host, port), Handler)
    instance.receipts = receipts
    return instance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--variant', action='append', required=True)
    parser.add_argument('--token-file', type=Path, required=True, help='Create individual credential if absent')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8443)
    parser.add_argument('--cert', type=Path)
    parser.add_argument('--key', type=Path)
    parser.add_argument('--allow-loopback-http', action='store_true', help='Local development only')
    parser.add_argument('--admin-token-file', type=Path)
    parser.add_argument('--selection-file', type=Path)
    parser.add_argument('--web-root', type=Path)
    parser.add_argument('--studio-port', type=int, default=18080)
    parser.add_argument('--ingest-token-file', type=Path, help='Dedicated existing consumable:submit credential')
    parser.add_argument('--ingest-root', type=Path, help='Private intake spool; never the ELO editorial workspace')
    parser.add_argument('--ingest-producer', help='Operator-assigned producer instance identity')
    args = parser.parse_args()
    try:
        insecure = args.allow_loopback_http
        if insecure and (args.host != '127.0.0.1' or args.cert or args.key):
            raise ValueError('HTTP development mode requires 127.0.0.1 and no TLS options')
        if not insecure and not (args.cert and args.key):
            raise ValueError('HTTPS requires --cert and --key')
        envelope(args.bundle, args.variant)  # Refuse invalid publication before listening.
        token = terminal_token(args.token_file, create=True)
        panel = None
        if args.admin_token_file:
            from elo_panel import Panel
            if not args.selection_file or not args.web_root:
                raise ValueError('Panel requires selection file and web root')
            admin_token = terminal_token(args.admin_token_file)
            if hmac.compare_digest(admin_token, token):
                raise ValueError('Admin and terminal credentials must be distinct')
            panel = Panel(args.bundle, args.variant, admin_token, args.selection_file, args.web_root, args.studio_port)
        ingest = None
        ingest_options = (args.ingest_token_file, args.ingest_root, args.ingest_producer)
        if any(ingest_options):
            if not all(ingest_options):
                raise ValueError('Ingest requires token file, private spool and producer identity')
            from elo_ingest import Ingest
            ingest = Ingest(args.ingest_root, terminal_token(args.ingest_token_file), args.ingest_producer)
        service = server(args.bundle, args.variant, token, args.host, args.port, panel=panel, ingest=ingest)
        if not insecure:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(args.cert, args.key)
            service.ssl_context = context
        print(f'ELO_DISTRIBUTION {"http" if insecure else "https"} {service.server_port}', flush=True)
        try:
            service.serve_forever()
        finally:
            service.server_close()
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
