#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Real Qt frames, unattended playback and supervisor recovery with no server."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from elo_content import activate, encoded
CLIENT = Path(os.environ.get('ELO_CLIENT_BIN', ROOT / 'build/client-fedora/elo-client')).resolve()
SUPERVISOR = ROOT / 'board/elo/qemu-gui/rootfs-overlay/usr/bin/elo-client-supervisor'


class AutomaticRecoveryTest(unittest.TestCase):
    def test_offline_recovery_after_kill_and_stalled_rendering(self):
        self.assertTrue(CLIENT.is_file(), 'Build native Qt client first')
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            runtime, cache = base / 'runtime', base / 'content'
            payload = encoded({'schema': 1, 'id': 'offline-recovery', 'name': 'Reprodução offline',
                'version': '4', 'exposure_seconds': 5, 'pages': [
                    {'title': 'Primeira', 'body': 'Começo automático.'},
                    {'title': 'Segunda', 'body': 'Continua sem servidor ou dispositivos de entrada.'}]})
            source = base / 'presentation.json'; source.write_bytes(payload)
            activate(cache, source, len(payload), hashlib.sha256(payload).hexdigest())
            environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                QT_FORCE_STDERR_LOGGING='1', ELO_RUNTIME_DIR=str(runtime),
                ELO_STARTUP_TIMEOUT_MS='5000', ELO_HEALTH_TIMEOUT_MS='3000',
                ELO_TERMINATE_GRACE_MS='200', ELO_BACKOFF_MS='100',
                ELO_MAX_BACKOFF_MS='200', ELO_POLL_SECONDS='0.1')
            with (base / 'log').open('w+') as output:
                proc = subprocess.Popen([str(SUPERVISOR), str(CLIENT), '--content-dir', str(cache)],
                    env=environment, stdout=output, stderr=output)
                def health():
                    try: return (runtime / 'health').read_text().split()
                    except FileNotFoundError: return []
                def wait(predicate, timeout=10):
                    deadline = time.monotonic() + timeout
                    while time.monotonic() < deadline:
                        frame = health()
                        if len(frame) == 8 and predicate(frame): return frame
                        if proc.poll() is not None: break
                        time.sleep(.05)
                    self.fail('Recovery timeout: ' + (base / 'log').read_text()[-2500:])
                try:
                    initial = wait(lambda x: x[5] in ('READY_LOCAL', 'DEGRADED_OFFLINE'))
                    for failure in (signal.SIGKILL, signal.SIGSTOP):
                        old_pid = initial[2]
                        os.kill(int(old_pid), failure)
                        initial = wait(lambda x: x[2] != old_pid and x[5] in ('READY_LOCAL', 'DEGRADED_OFFLINE'))
                        self.assertNotEqual(initial[1], '')
                        wait(lambda x: x[2] == initial[2] and x[6] == '2')
                    self.assertIn('presentation-stalled', (base / 'log').read_text())
                    self.assertIsNone(proc.poll())
                    self.assertEqual(hashlib.sha256(payload).hexdigest(), json.loads((cache / 'active.json').read_text())['bundle'])
                finally:
                    proc.terminate()
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill(); proc.wait(timeout=5)
                self.assertFalse((runtime / 'child.pid').exists())


if __name__ == '__main__':
    unittest.main()
