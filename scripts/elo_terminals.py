#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Individual terminal credentials and latest reports, never administrative credentials."""
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import tempfile
import threading
from elo_content import decode, encoded, sync_dir
from elo_receipts import Receipts
from elo_control import Control


class Terminals:
    def __init__(self, path, local_receipts):
        self.path = Path(path)
        self.local_receipts = local_receipts
        self.lock = threading.RLock()
        self.items = decode(self.path.read_bytes()) if self.path.exists() else {}
        self.reports = {}
        self.control = Control(self.path.parent / 'control.json')

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.terminals-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(encoded(self.items)); stream.flush(); os.fsync(stream.fileno())
            os.replace(name, self.path); sync_dir(self.path.parent)
        finally: Path(name).unlink(missing_ok=True)

    def add(self, value):
        if (not isinstance(value, dict) or set(value) != {'name'} or not isinstance(value['name'], str)
                or not value['name'].strip() or len(value['name'].encode()) > 80
                or any(ord(c) < 32 for c in value['name'])):
            raise ValueError('Invalid terminal name')
        with self.lock:
            if len(self.items) >= 100: raise ValueError('Terminal limit reached')
            identity = secrets.token_hex(8)
            credential = secrets.token_urlsafe(32)
            self.items[identity] = {'name': value['name'].strip(),
                'token_sha256': hashlib.sha256(credential.encode()).hexdigest(), 'revoked': False}
            self.save()
            return {'id': identity, 'name': self.items[identity]['name'], 'token': credential}

    def authenticate(self, credential):
        digest = hashlib.sha256(credential).hexdigest()
        with self.lock:
            for identity, item in self.items.items():
                if not item['revoked'] and hmac.compare_digest(digest, item['token_sha256']): return identity
        return None

    def receipt(self, identity):
        if identity == 'local': return self.local_receipts
        with self.lock:
            if identity not in self.items: raise ValueError('Unknown terminal')
            if identity not in self.reports:
                self.reports[identity] = Receipts(self.path.parent / 'terminals' / identity / 'receipt.json')
            return self.reports[identity]

    def revoke(self, identity):
        with self.lock:
            if identity not in self.items: raise ValueError('Unknown terminal')
            self.items[identity]['revoked'] = True
            self.save()
            self.control.cancel(identity)
        return {'revoked': True}

    def power(self, identity, value):
        with self.lock:
            if identity not in self.items or self.items[identity]['revoked']:
                raise ValueError('Totem desconhecido ou revogado')
            return self.control.request(identity, value)

    def status(self, expected):
        with self.lock:
            items = {'local': {'name': 'PC de testes', 'revoked': False}, **self.items}
            return [dict(id=identity, name=item['name'], revoked=item['revoked'],
                         control=self.control.status(identity),
                         **self.receipt(identity).status(expected)) for identity, item in items.items()]
