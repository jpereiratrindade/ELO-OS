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
from elo_telemetry import TelemetryStore


class Receipts:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.history_path = (self.path.parent / 'history.json') if self.path else None
        self.telemetry = TelemetryStore(self.path.parent / 'telemetry.sqlite3') if self.path else None
        self.lock = threading.RLock()
        self.record = None
        self.history = []
        if self.path:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.path and self.path.exists():
            if self.path.is_symlink() or self.path.stat().st_size > 4096:
                raise ValueError('Invalid receipt store')
            self.record = decode(self.path.read_bytes())
        if self.history_path and self.history_path.exists():
            try:
                if not self.history_path.is_symlink() and self.history_path.stat().st_size <= 65536:
                    loaded = decode(self.history_path.read_bytes())
                    if isinstance(loaded, list):
                        self.history = loaded
            except Exception:
                self.history = []

    def accept(self, value):
        fields = {'schema', 'session', 'sequence', 'received_sha256', 'presented_sha256'}
        if isinstance(value, dict) and value.get('schema') == 2: fields = fields | {'display'}
        if isinstance(value, dict) and 'telemetry' in value: fields = fields | {'telemetry'}
        if not isinstance(value, dict) or set(value) != fields or type(value['schema']) is not int or value['schema'] not in (1, 2):
            raise ValueError('Invalid report schema')
        if (not isinstance(value['session'], str) or not re.fullmatch(r'[a-f0-9-]{36}', value['session'])
                or type(value['sequence']) is not int or not 1 <= value['sequence'] <= 2**53 - 1):
            raise ValueError('Invalid report sequence/session')
        for key in ('received_sha256', 'presented_sha256'):
            if not isinstance(value[key], str) or (value[key] and not re.fullmatch(r'[a-f0-9]{64}', value[key])):
                raise ValueError('Invalid content digest')
        if not value['received_sha256'] and not value['presented_sha256']:
            raise ValueError('Empty report')
        if value['schema'] == 2:
            display = value['display']
            if not isinstance(display, dict) or set(display) != {'publication', 'title', 'page', 'pages', 'mode', 'exposure_seconds'}:
                raise ValueError('Invalid display report')
            for key, limit in (('publication', 512), ('title', 256)):
                if not isinstance(display[key], str) or not display[key] or len(display[key].encode()) > limit or any(ord(c) < 32 for c in display[key]):
                    raise ValueError('Invalid display text')
            if (not value['presented_sha256'] or type(display['page']) is not int or type(display['pages']) is not int
                    or not 1 <= display['page'] <= display['pages'] <= 32
                    or type(display['exposure_seconds']) is not int
                    or display['mode'] not in ('automatic', 'manual')
                    or (display['mode'] == 'automatic' and not 5 <= display['exposure_seconds'] <= 3600)
                    or (display['mode'] == 'manual' and display['exposure_seconds'] != 0)):
                raise ValueError('Invalid display state')
        with self.lock:
            if self.record and self.record['session'] == value['session'] and value['sequence'] <= self.record['sequence']:
                if value == {key: self.record.get(key) for key in fields}:
                    return  # Idempotent resend does not renew freshness.
                raise ValueError('Stale or conflicting report')
            now = time.time()
            record = dict(value, seen_at=now)

            event = None
            display = value.get('display') or {}
            page_info = f"Pág. {display['page']}/{display['pages']}: {display['title']}" if display.get('page') else None

            if not self.record:
                event = {
                    'time': now,
                    'type': 'connected',
                    'label': 'Primeira comunicação registrada',
                    'session': value['session'],
                    'detail': page_info
                }
            else:
                elapsed = now - self.record['seen_at']
                new_session = value['session'] != self.record['session']
                if new_session:
                    if elapsed >= 90:
                        pre_tele = self.telemetry.latest() if self.telemetry else None
                        tele_summary = ""
                        if pre_tele:
                            parts = []
                            if pre_tele.get('cpu_temp_c') is not None: parts.append(f"{pre_tele['cpu_temp_c']}°C")
                            if pre_tele.get('voltage_v') is not None: parts.append(f"{pre_tele['voltage_v']}V")
                            if pre_tele.get('cpu_load_1m') is not None: parts.append(f"carga {pre_tele['cpu_load_1m']}")
                            if parts: tele_summary = " · Estado pré-queda: " + ", ".join(parts)
                        event = {
                            'time': now,
                            'type': 'reboot_after_drop',
                            'label': f'Reinício do totem após queda ({self._format_duration(elapsed)}){tele_summary}',
                            'downtime_seconds': int(elapsed),
                            'session': value['session'],
                            'detail': page_info,
                            'pre_drop_telemetry': pre_tele
                        }
                    else:
                        event = {
                            'time': now,
                            'type': 'reboot',
                            'label': 'Reinício do aparelho (nova sessão)',
                            'session': value['session'],
                            'detail': page_info
                        }
                elif elapsed >= 90:
                    pre_tele = self.telemetry.latest() if self.telemetry else None
                    tele_summary = ""
                    if pre_tele:
                        parts = []
                        if pre_tele.get('cpu_temp_c') is not None: parts.append(f"{pre_tele['cpu_temp_c']}°C")
                        if pre_tele.get('voltage_v') is not None: parts.append(f"{pre_tele['voltage_v']}V")
                        if parts: tele_summary = " · Estado pré-queda: " + ", ".join(parts)
                    event = {
                        'time': now,
                        'type': 'reconnected',
                        'label': f'Reconexão após {self._format_duration(elapsed)} sem sinal{tele_summary}',
                        'downtime_seconds': int(elapsed),
                        'session': value['session'],
                        'detail': page_info,
                        'pre_drop_telemetry': pre_tele
                    }

            if event:
                self.history.append(event)
                if len(self.history) > 50:
                    self.history = self.history[-50:]
                self._save_history()

            if 'telemetry' in value and self.telemetry:
                self.telemetry.record(value['telemetry'], now=now)

            if self.path:
                fd, name = tempfile.mkstemp(prefix='.receipt-', dir=self.path.parent)
                try:
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(encoded(record)); stream.flush(); os.fsync(stream.fileno())
                    os.replace(name, self.path); sync_dir(self.path.parent)
                finally:
                    Path(name).unlink(missing_ok=True)
            self.record = record

    def _save_history(self):
        if not self.history_path:
            return
        fd, name = tempfile.mkstemp(prefix='.history-', dir=self.history_path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(encoded(self.history)); stream.flush(); os.fsync(stream.fileno())
            os.replace(name, self.history_path); sync_dir(self.history_path.parent)
        finally:
            Path(name).unlink(missing_ok=True)

    @staticmethod
    def _format_duration(seconds):
        seconds = max(0, int(seconds))
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        if minutes < 60:
            rem = seconds % 60
            return f"{minutes}min {rem}s" if rem else f"{minutes}min"
        hours = minutes // 60
        rem_min = minutes % 60
        return f"{hours}h {rem_min}min" if rem_min else f"{hours}h"

    def status(self, expected, now=None):
        now = time.time() if now is None else now
        with self.lock:
            record = dict(self.record) if self.record else None
            events = list(self.history)
        if not record:
            return {'state': 'unconfirmed', 'label': 'Sem confirmação do cliente', 'last_seen': None, 'events': events}
        age = now - record['seen_at']
        fresh = 0 <= age < 90
        downtime_label = self._format_duration(age) if not fresh else None
        if not fresh:
            state, label = 'stale', 'Sem contato recente'
        elif expected and record['presented_sha256'] == expected:
            state, label = 'presented', 'Apresentação confirmada'
        elif expected and record['received_sha256'] == expected:
            state, label = 'received', 'Recebido · aguardando aplicação'
        else:
            state, label = 'pending', 'Atualização pendente'
        return {'state': state, 'label': label, 'last_seen': record['seen_at'],
                'received_sha256': record['received_sha256'], 'presented_sha256': record['presented_sha256'],
                'display': record.get('display'), 'recent': fresh,
                'events': events[-10:], 'downtime_seconds': int(age) if not fresh else 0,
                'downtime_label': downtime_label,
                'telemetry': self.telemetry.latest() if self.telemetry else None}
