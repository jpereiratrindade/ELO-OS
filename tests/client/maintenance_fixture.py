# SPDX-License-Identifier: GPL-3.0-only
"""Isolated NTP and HTTPS peers for the ARM64 maintenance integration test."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import socket
import ssl
import struct
import subprocess
import threading
import time


class MaintenanceFixture:
    def __init__(self, base, payload):
        self.base = base
        self.downloads = 0
        self.report = None
        self.ntp_requests = 0
        self.stop = threading.Event()
        self.key = base / 'ssh-key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(self.key)], check=True)
        self.public = base / 'ssh-key.pub'
        self.cert = base / 'ca.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
            '-subj', '/CN=elo-maintenance-test', '-addext', 'subjectAltName=IP:10.0.2.2',
            '-keyout', str(base / 'tls.key'), '-out', str(self.cert)], check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        envelope = json.dumps({'schema': 1, 'sha256': hashlib.sha256(payload).hexdigest(),
            'size': len(payload), 'presentation': payload.decode(), 'source': {}}).encode()
        fixture = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def reply(self, status, body):
                self.send_response(status); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_GET(self):
                if self.headers.get('Authorization') != 'Bearer ' + 't' * 43: self.reply(401, b'{}'); return
                fixture.downloads += 1
                self.reply(200, envelope)
            def do_POST(self):
                if self.headers.get('Authorization') != 'Bearer ' + 't' * 43: self.reply(401, b'{}'); return
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 2048: self.reply(400, b'{}'); return
                fixture.report = json.loads(self.rfile.read(size))
                self.reply(200, b'{}')
        self.https = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(self.cert, base / 'tls.key')
        self.https.socket = tls.wrap_socket(self.https.socket, server_side=True)
        threading.Thread(target=self.https.serve_forever, daemon=True).start()
        self.ntp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ntp.bind(('127.0.0.1', 0)); self.ntp.settimeout(.2)
        threading.Thread(target=self.serve_ntp, daemon=True).start()
        reservation = socket.socket(); reservation.bind(('127.0.0.1', 0))
        self.ssh_port = reservation.getsockname()[1]; reservation.close()

    def serve_ntp(self):
        def stamp(value):
            seconds = int(value) + 2208988800
            return struct.pack('!II', seconds, int((value - int(value)) * 2**32))
        while not self.stop.is_set():
            try: request, peer = self.ntp.recvfrom(512)
            except socket.timeout: continue
            except OSError: return
            if len(request) < 48: continue
            self.ntp_requests += 1
            now = time.time()
            response = bytes([0x24, 1, 4, 236]) + struct.pack('!II', 0, 64) + b'LOCL'
            response += stamp(now - 1) + request[40:48] + stamp(now) + stamp(time.time())
            self.ntp.sendto(response, peer)

    def ssh(self, command, key=None):
        return subprocess.run(['ssh', '-i', str(key or self.key), '-p', str(self.ssh_port),
            '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'PasswordAuthentication=no',
            '-o', 'StrictHostKeyChecking=accept-new', '-o', 'UserKnownHostsFile=' + str(self.base / 'known_hosts'),
            '-o', 'ConnectTimeout=5', 'root@127.0.0.1', command], capture_output=True, text=True, timeout=25)

    def close(self):
        self.stop.set(); self.ntp.close(); self.https.shutdown(); self.https.server_close()
