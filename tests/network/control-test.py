#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Power control authorization, expiry, replay protection, and real HTTPS agent."""
import importlib.util
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
import uuid
import http.client
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from elo_content import decode, encoded
from elo_control import Control
from elo_server import server
spec = importlib.util.spec_from_file_location('panel_tests', Path(__file__).with_name('panel-test.py'))
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
BOOT = str(uuid.uuid4())


def poll_value(boot=BOOT): return {'schema': 1, 'boot_id': boot}
def request_value(action='reboot'): return {'action': action, 'request_id': str(uuid.uuid4())}
def ack_value(command, result='accepted', boot=BOOT):
    return {'schema': 1, 'boot_id': boot, 'command_id': command['id'], 'result': result}


class ControlTest(unittest.TestCase):
    setUp = fixtures.PanelTest.setUp
    stop = fixtures.PanelTest.stop
    request = fixtures.PanelTest.request

    def terminal(self):
        status, body = self.request('/manage/terminals', 'POST', {'name': 'Pi de teste'})
        self.assertEqual(status, 201)
        return decode(body)

    def announce(self, terminal):
        self.assertEqual(self.request('/v1/control/poll', 'POST', poll_value(), terminal['token'].encode())[0], 200)

    def test_admin_only_and_capability_required(self):
        terminal = self.terminal()
        route = f"/manage/terminals/{terminal['id']}/power"
        self.assertEqual(self.request(route, 'POST', request_value())[0], 400)
        self.announce(terminal)
        for token in (None, b't' * 43, terminal['token'].encode()):
            self.assertEqual(self.request(route, 'POST', request_value(), token)[0], 401)
        self.assertEqual(self.request(route, 'POST', request_value(), origin='https://evil.example')[0], 403)
        self.assertEqual(self.request(route, 'POST', request_value('sh -c reboot'))[0], 400)
        self.assertEqual(self.request('/v1/control/poll', 'POST', poll_value(), b't' * 43)[0], 401)
        self.assertEqual(self.request('/v1/control/poll', 'POST', poll_value(), b'a' * 43)[0], 401)
        self.assertEqual(self.request('/manage/terminals/local/power', 'POST', request_value())[0], 404)

    def test_target_binding_idempotence_and_revocation(self):
        first, second = self.terminal(), self.terminal()
        self.announce(first); self.announce(second)
        route = f"/manage/terminals/{first['id']}/power"
        value = request_value('poweroff')
        status, body = self.request(route, 'POST', value)
        self.assertEqual(status, 202)
        command = decode(body)
        self.assertEqual(decode(self.request(route, 'POST', value)[1])['id'], command['id'])
        self.assertEqual(self.request(route, 'POST', request_value())[0], 400)
        self.assertIsNone(decode(self.request('/v1/control/poll', 'POST', poll_value(), second['token'].encode())[1])['command'])
        self.assertEqual(self.request('/v1/control/ack', 'POST', ack_value(command), second['token'].encode())[0], 400)
        self.assertEqual(self.request('/v1/control/ack', 'POST', ack_value(command), first['token'].encode())[0], 200)
        self.assertEqual(self.request('/v1/control/ack', 'POST', ack_value(command), first['token'].encode())[0], 200)
        self.assertIsNone(decode(self.request('/v1/control/poll', 'POST', poll_value(), first['token'].encode())[1])['command'])
        self.request(f"/manage/terminals/{first['id']}/revoke", 'POST')
        self.assertEqual(self.request('/v1/control/poll', 'POST', poll_value(), first['token'].encode())[0], 401)
        self.assertEqual(self.request(route, 'POST', request_value())[0], 400)

    def test_invalid_control_envelopes(self):
        terminal = self.terminal()
        for data in ({}, {'schema': True, 'boot_id': BOOT}, {'schema': 1, 'boot_id': '../../etc'}, {'schema': 1, 'boot_id': BOOT, 'action': 'reboot'}):
            self.assertEqual(self.request('/v1/control/poll', 'POST', data, terminal['token'].encode())[0], 400)


class ControlLifetimeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.now = 1000
        self.path = Path(self.temp.name) / 'control.json'
        self.control = Control(self.path, lambda: self.now)
        self.control.poll('pi', poll_value())

    def test_offline_and_expired_commands_never_deliver(self):
        command = self.control.request('pi', request_value())
        self.now += 31
        self.assertFalse(self.control.status('pi')['available'])
        self.now += 90
        self.assertIsNone(self.control.poll('pi', poll_value())['command'])
        self.assertEqual(self.control.status('pi')['command']['state'], 'expired')
        with self.assertRaises(ValueError): self.control.acknowledge('pi', ack_value(command))

    def test_persistence_boot_binding_and_restart_observation(self):
        command = self.control.request('pi', request_value())
        restored = Control(self.path, lambda: self.now)
        self.assertFalse(restored.status('pi')['available'])
        self.assertEqual(restored.poll('pi', poll_value())['command']['id'], command['id'])
        restored.acknowledge('pi', ack_value(command))
        restored.poll('pi', poll_value(str(uuid.uuid4())))
        self.assertEqual(restored.status('pi')['command']['state'], 'reboot_observed')

    def test_new_boot_cancels_pending_and_shutdown_not_claimed(self):
        self.control.request('pi', request_value())
        newboot = str(uuid.uuid4())
        self.assertIsNone(self.control.poll('pi', poll_value(newboot))['command'])
        self.assertEqual(self.control.status('pi')['command']['state'], 'cancelled')
        command = self.control.request('pi', request_value('poweroff'))
        self.control.acknowledge('pi', ack_value(command, boot=newboot))
        self.now += 121
        self.assertEqual(self.control.status('pi')['command']['state'], 'unconfirmed')
        self.control.poll('pi', poll_value(str(uuid.uuid4())))
        self.assertEqual(self.control.status('pi')['command']['state'], 'unconfirmed')

    def test_old_reboot_not_attributed_to_future_boot(self):
        command = self.control.request('pi', request_value())
        self.control.acknowledge('pi', ack_value(command))
        self.now += 3600
        self.control.poll('pi', poll_value(str(uuid.uuid4())))
        self.assertEqual(self.control.status('pi')['command']['state'], 'unconfirmed')

    def test_revocation_cancels_pending(self):
        self.control.request('pi', request_value())
        self.control.cancel('pi')
        self.assertIsNone(self.control.poll('pi', poll_value())['command'])


@unittest.skipUnless(os.environ.get('ELO_CONTROL_TEST_AGENT_BIN'), 'Set native test-only agent path for HTTPS integration')
class AgentTest(unittest.TestCase):
    setUpFixture = fixtures.PanelTest.setUp
    stop = fixtures.PanelTest.stop

    def setUp(self):
        self.setUpFixture()
        self.service.shutdown(); self.service.server_close()
        root = Path(self.temp.name)
        cert, key = root / 'server.crt', root / 'server.key'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1', '-subj', '/CN=control-test.invalid',
                        '-addext', 'subjectAltName=IP:127.0.0.1', '-keyout', str(key), '-out', str(cert)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.service = server(self.bundle, ['v1'], b't' * 43, panel=self.panel)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(cert, key)
        self.service.socket = context.wrap_socket(self.service.socket, server_side=True)
        threading.Thread(target=self.service.serve_forever, daemon=True).start()
        self.terminal = self.panel.terminals.add({'name': 'Pi simulado'})
        self.config, self.state = root / 'config', root / 'agent-state'
        self.config.mkdir()
        (self.config / 'server.url').write_text(f'https://127.0.0.1:{self.service.server_port}/v1/presentation')
        (self.config / 'terminal.token').write_text(self.terminal['token']); (self.config / 'terminal.token').chmod(0o600)
        (self.config / 'ca.pem').write_bytes(cert.read_bytes())
        self.proc = None
        self.addCleanup(self.kill)

    def kill(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate(); self.proc.wait(timeout=10)

    def launch(self):
        self.proc = subprocess.Popen([os.environ['ELO_CONTROL_TEST_AGENT_BIN'], '--config-dir', str(self.config), '--state-dir', str(self.state)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def wait_for(self, predicate):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if predicate(): return
            if self.proc and self.proc.poll() is not None: self.fail(f'Agent exited {self.proc.returncode}')
            time.sleep(.1)
        self.fail('Agent did not reach expected state')

    def test_https_execution_and_replay_after_agent_restart(self):
        self.launch()
        identity = self.terminal['id']
        self.wait_for(lambda: self.panel.terminals.control.status(identity)['available'])
        value = request_value()
        self.panel.terminals.power(identity, value)
        executed = self.state / 'executed'
        self.wait_for(executed.exists)
        self.assertEqual(executed.read_text().splitlines(), [value['request_id'] + ' reboot'])
        self.kill()
        # Simulate a repeated delivery of the already consumed command.
        self.panel.terminals.control.commands[identity]['state'] = 'pending'
        self.launch()
        self.wait_for(lambda: self.panel.terminals.control.status(identity)['command']['state'] == 'failed')
        self.assertEqual(executed.read_text().splitlines(), [value['request_id'] + ' reboot'])

    def test_failed_ack_never_executes(self):
        original = self.panel.terminals.control.acknowledge
        def lose_ack(identity, value):
            if value['result'] == 'accepted': raise ValueError('Simulated lost acknowledgement')
            return original(identity, value)
        self.panel.terminals.control.acknowledge = lose_ack
        self.launch()
        identity = self.terminal['id']
        self.wait_for(lambda: self.panel.terminals.control.status(identity)['available'])
        self.panel.terminals.power(identity, request_value('poweroff'))
        self.wait_for(lambda: self.panel.terminals.control.status(identity)['command']['state'] == 'failed')
        self.assertFalse((self.state / 'executed').exists())

    def test_tls_hostname_mismatch_never_registers_agent(self):
        (self.config / 'server.url').write_text(f'https://localhost:{self.service.server_port}/v1/presentation')
        self.launch(); time.sleep(2)
        self.assertFalse(self.panel.terminals.control.status(self.terminal['id'])['supported'])
        self.assertFalse((self.state / 'executed').exists())


if __name__ == '__main__': unittest.main()
