#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Read-only ELO text distribution service, protocol 1 (one terminal credential)."""
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

from elo_content import encoded
from elo_import import project
from elo_receipts import Receipts


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


def envelope(bundle, variants):
    data, source = project(bundle, variants)
    return encoded({'schema': 1, 'sha256': hashlib.sha256(data).hexdigest(),
                    'size': len(data), 'presentation': data.decode('utf-8'),
                    'source': {'bundle_id': source['bundle_id'], 'version': source['version'],
                               'content_hash': source['content_hash'], 'variants': variants}})


def server(bundle, variants, token, host='127.0.0.1', port=0, panel=None):
    receipts = panel.receipts if panel else Receipts()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Never log request headers, token, query or content.

        def respond(self, status, body, content_type='application/json; charset=utf-8', extra_headers=()):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            for name, value in extra_headers:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def authorized(self, credential):
            auth = self.headers.get_all('Authorization', [])
            return len(auth) == 1 and hmac.compare_digest(auth[0].encode('utf-8'), b'Bearer ' + credential)

        def admin_request(self, method):
            if not panel or not self.authorized(panel.token):
                self.respond(401, b'{"error":"unauthorized"}')
                return
            scheme = 'https' if isinstance(self.connection, ssl.SSLSocket) else 'http'
            allowed = {f'{scheme}://localhost:{self.server.server_port}', f'{scheme}://127.0.0.1:{self.server.server_port}'}
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
                elif self.path == '/manage/delivery' and method == 'GET':
                    self.respond(200, encoded(panel.delivery()))
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
            except (OSError, ValueError, UnicodeError):
                self.respond(400, encoded({'error': 'Operação recusada. Confira publicação, seleção e disponibilidade do Estúdio.'}))
            except Exception:
                self.respond(502, b'{"error":"editorial_service_unavailable"}')

        def do_POST(self):
            if self.path == '/v1/receipt':
                if not self.authorized(token):
                    self.respond(401, b'{"error":"unauthorized"}')
                    return
                try:
                    from elo_content import decode
                    size = int(self.headers.get('Content-Length', '0'))
                    if self.headers.get('Transfer-Encoding') or not 1 <= size <= 2048:
                        raise ValueError('Invalid receipt size')
                    receipts.accept(decode(self.rfile.read(size)))
                    self.respond(200, b'{"accepted":true}')
                except (ValueError, OSError, UnicodeError):
                    self.respond(400, b'{"error":"receipt_rejected"}')
                return
            self.admin_request('POST')

        def do_PUT(self):
            self.admin_request('PUT')

        def do_DELETE(self):
            self.admin_request('DELETE')

        def do_GET(self):
            assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/panel.css': ('panel.css', 'text/css; charset=utf-8'),
                      '/panel.js': ('panel.js', 'text/javascript; charset=utf-8'),
                      '/studio/': ('studio/index.html', 'text/html; charset=utf-8'),
                      '/studio/app.css': ('studio/app.css', 'text/css; charset=utf-8'),
                      '/studio/theme.css': ('studio-morfo.css', 'text/css; charset=utf-8'),
                      '/studio/app.js': ('studio/app.js', 'text/javascript; charset=utf-8')}
            if panel and self.path in assets:
                filename, mime = assets[self.path]
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
            if not self.authorized(token):
                self.respond(401, b'{"error":"unauthorized"}')
                return
            if self.path != '/v1/presentation':
                self.respond(404, b'{"error":"not_found"}')
                return
            try:
                body = envelope(bundle, panel.variants() if panel else variants)
                from elo_content import decode
                if decode(decode(body)['presentation'].encode())['version'] == '2' and 'image-v2' not in self.headers.get('X-ELO-Capabilities', '').split(','):
                    self.respond(409, b'{"error":"image_capability_required"}')
                    return
            except (OSError, ValueError, UnicodeError, KeyError):
                self.respond(503, b'{"error":"publication_unavailable"}')
                return
            self.respond(200, body)

    class Server(ThreadingHTTPServer):
        daemon_threads = True

        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(10)
            return connection, address

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
        service = server(args.bundle, args.variant, token, args.host, args.port, panel=panel)
        if not insecure:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(args.cert, args.key)
            service.socket = context.wrap_socket(service.socket, server_side=True)
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
