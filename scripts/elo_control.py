#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bounded, expiring terminal power requests. Never accepts shell commands."""
import os
from pathlib import Path
import re
import tempfile
import threading
import time
import uuid
from elo_content import decode, encoded, sync_dir

UUID = re.compile(r'[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}')


class Control:
    def __init__(self, path, clock=time.time):
        self.path = Path(path)
        self.clock = clock
        self.lock = threading.RLock()
        self.commands = decode(self.path.read_bytes()) if self.path.exists() else {}
        self.agents = {}

    def save(self):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.control-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(encoded(self.commands)); stream.flush(); os.fsync(stream.fileno())
            os.replace(name, self.path); sync_dir(self.path.parent)
        finally:
            Path(name).unlink(missing_ok=True)

    def expire(self, identity):
        command = self.commands.get(identity)
        if command and command['state'] in ('pending', 'accepted') and self.clock() >= command['expires_at']:
            command['state'] = 'expired' if command['state'] == 'pending' else 'unconfirmed'
            self.save()
        return command

    def status(self, identity):
        with self.lock:
            agent = self.agents.get(identity)
            command = self.expire(identity)
            online = bool(agent and 0 <= self.clock() - agent['seen_at'] < 30)
            return {'available': online, 'supported': bool(agent),
                    'busy': bool(command and command['state'] in ('pending', 'accepted')),
                    'last_seen': agent['seen_at'] if agent else None,
                    'command': dict(command) if command else None}

    def request(self, identity, value):
        if not isinstance(value, dict) or set(value) != {'action', 'request_id'}:
            raise ValueError('Comando inválido')
        if value['action'] not in ('reboot', 'poweroff') or not isinstance(value['request_id'], str) or not UUID.fullmatch(value['request_id']):
            raise ValueError('Comando inválido')
        with self.lock:
            existing = self.expire(identity)
            if existing and existing['id'] == value['request_id']:
                if existing['action'] != value['action']: raise ValueError('Comando conflitante')
                return dict(existing)
            status = self.status(identity)
            if not status['available']: raise ValueError('Manutenção indisponível. Aguarde contato do totem.')
            if status['busy']: raise ValueError('Já existe um comando em andamento para este totem.')
            now = self.clock()
            command = {'id': value['request_id'], 'action': value['action'], 'state': 'pending',
                       'requested_at': now, 'expires_at': now + 120,
                       'boot_id': self.agents[identity]['boot_id']}
            self.commands[identity] = command
            self.save()
            return dict(command)

    def poll(self, identity, value):
        if (not isinstance(value, dict) or not set(value).issubset({'schema', 'boot_id', 'telemetry'})
                or not {'schema', 'boot_id'}.issubset(set(value)) or type(value['schema']) is not int
                or value['schema'] != 1 or not isinstance(value['boot_id'], str) or not UUID.fullmatch(value['boot_id'])):
            raise ValueError('Invalid control agent report')
        with self.lock:
            command = self.expire(identity)
            boot_id = value['boot_id']
            if command and command['boot_id'] != boot_id:
                if (command['state'] in ('accepted', 'unconfirmed') and command['action'] == 'reboot'
                        and self.clock() <= command['expires_at'] + 180):
                    command['state'] = 'reboot_observed'
                    self.save()
                elif command['state'] == 'pending':
                    command['state'] = 'cancelled'
                    self.save()
            self.agents[identity] = {'boot_id': boot_id, 'seen_at': self.clock()}
            if 'telemetry' in value:
                try:
                    from elo_telemetry import TelemetryStore
                    db_dir = self.path.parent / 'terminals' / identity if identity != 'local' else self.path.parent
                    TelemetryStore(db_dir / 'telemetry.sqlite3').record(value['telemetry'], now=self.clock())
                except Exception:
                    pass
            result = {'schema': 1, 'command': None}
            if command and command['state'] == 'pending':
                result['command'] = dict(command, remaining_seconds=max(0, int(command['expires_at'] - self.clock())))
            return result

    def acknowledge(self, identity, value):
        if (not isinstance(value, dict) or set(value) != {'schema', 'boot_id', 'command_id', 'result'}
                or type(value['schema']) is not int or value['schema'] != 1
                or value['result'] not in ('accepted', 'failed')):
            raise ValueError('Invalid acknowledgement')
        with self.lock:
            command = self.expire(identity)
            if (not command or command['id'] != value['command_id'] or command['boot_id'] != value['boot_id']
                    or command['state'] not in ('pending', 'accepted', 'failed')):
                raise ValueError('Comando expirado ou não pertence a este totem.')
            if command['state'] == 'failed' and value['result'] != 'failed': raise ValueError('Comando já falhou')
            command['state'] = value['result']
            command['acknowledged_at'] = self.clock()
            self.save()
            return {'schema': 1, 'accepted': True, 'command_id': command['id']}

    def cancel(self, identity):
        with self.lock:
            command = self.expire(identity)
            if command and command['state'] == 'pending':
                command['state'] = 'cancelled'
                self.save()
