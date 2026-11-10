#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Latest authenticated terminal report, not an interaction-event queue."""
import os
from pathlib import Path
import re
import tempfile
import threading
import time
from elo_content import decode, encoded, sync_dir


class Receipts:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.lock = threading.RLock()
        self.record = None
        if self.path:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.path and self.path.exists():
            if self.path.is_symlink() or self.path.stat().st_size > 4096:
                raise ValueError('Invalid receipt store')
            self.record = decode(self.path.read_bytes())

    def accept(self, value):
        fields = {'schema', 'session', 'sequence', 'received_sha256', 'presented_sha256'}
        if not isinstance(value, dict) or set(value) != fields or type(value['schema']) is not int or value['schema'] != 1:
            raise ValueError('Invalid report schema')
        if (not isinstance(value['session'], str) or not re.fullmatch(r'[a-f0-9-]{36}', value['session'])
                or type(value['sequence']) is not int or not 1 <= value['sequence'] <= 2**53 - 1):
            raise ValueError('Invalid report sequence/session')
        for key in ('received_sha256', 'presented_sha256'):
            if not isinstance(value[key], str) or (value[key] and not re.fullmatch(r'[a-f0-9]{64}', value[key])):
                raise ValueError('Invalid content digest')
        if not value['received_sha256'] and not value['presented_sha256']:
            raise ValueError('Empty report')
        with self.lock:
            if self.record and self.record['session'] == value['session'] and value['sequence'] <= self.record['sequence']:
                if value == {key: self.record[key] for key in fields}:
                    return  # Idempotent resend does not renew freshness.
                raise ValueError('Stale or conflicting report')
            record = dict(value, seen_at=time.time())
            if self.path:
                fd, name = tempfile.mkstemp(prefix='.receipt-', dir=self.path.parent)
                try:
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(encoded(record)); stream.flush(); os.fsync(stream.fileno())
                    os.replace(name, self.path); sync_dir(self.path.parent)
                finally:
                    Path(name).unlink(missing_ok=True)
            self.record = record

    def status(self, expected, now=None):
        now = time.time() if now is None else now
        with self.lock:
            record = dict(self.record) if self.record else None
        if not record:
            return {'state': 'unconfirmed', 'label': 'Sem confirmação do cliente', 'last_seen': None}
        age = now - record['seen_at']
        fresh = 0 <= age < 90
        if not fresh:
            state, label = 'stale', 'Sem contato recente'
        elif expected and record['presented_sha256'] == expected:
            state, label = 'presented', 'Apresentação confirmada'
        elif expected and record['received_sha256'] == expected:
            state, label = 'received', 'Recebido · aguardando Recomeçar'
        else:
            state, label = 'pending', 'Atualização pendente'
        return {'state': state, 'label': label, 'last_seen': record['seen_at'],
                'received_sha256': record['received_sha256'], 'presented_sha256': record['presented_sha256']}
