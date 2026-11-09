#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
SUPERVISOR = ROOT / 'board/elo/qemu-gui/rootfs-overlay/usr/bin/elo-client-supervisor'


class SupervisorTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.runtime = self.directory / 'run'
        self.log = self.directory / 'supervisor.log'
        self.proc = None
        self.addCleanup(self.stop)

    def start(self, mode='normal'):
        env = {**os.environ, 'ELO_RUNTIME_DIR': str(self.runtime), 'ELO_FAKE_MODE': mode,
               'ELO_STARTUP_TIMEOUT_MS': '500', 'ELO_HEALTH_TIMEOUT_MS': '500',
               'ELO_TERMINATE_GRACE_MS': '100', 'ELO_BACKOFF_MS': '100',
               'ELO_MAX_BACKOFF_MS': '200', 'ELO_RESTART_WINDOW_MS': '60000',
               'ELO_RESTART_LIMIT': '2', 'ELO_STABLE_MS': '10000', 'ELO_POLL_SECONDS': '0.1'}
        shell = shlex.split(os.environ.get('ELO_SUPERVISOR_SHELL', '/bin/sh'))
        if Path(shell[0]).name == 'busybox':
            binary = Path(shell[0]).resolve()
            commands = self.directory / 'bin'
            commands.mkdir(exist_ok=True)
            for name in ('cat', 'chmod', 'flock', 'mkdir', 'mv', 'rm', 'sleep'):
                (commands / name).symlink_to(binary)
            env['PATH'] = str(commands) + os.pathsep + env.get('PATH', '/usr/bin:/bin')
        self.command = [*shell, str(SUPERVISOR), sys.executable,
                        str(ROOT / 'tests/client/fake-presentation.py')]
        self.env = env
        with self.log.open('wb') as output:
            self.proc = subprocess.Popen(self.command,
                                         env=env, stdout=output, stderr=subprocess.STDOUT,
                                         start_new_session=True)

    def wait_for(self, predicate, timeout=4):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                value = predicate()
                if value:
                    return value
            except (OSError, ValueError, IndexError):
                pass
            time.sleep(0.02)
        self.fail(f'criterion not reached; log={self.log.read_text()}')

    def health(self):
        fields = (self.runtime / 'health').read_text().split()
        if len(fields) != 8 or fields[0] != 'ELO_HEALTH_V1':
            return None
        return fields

    def ready(self):
        def criterion():
            fields = self.health()
            pid = int((self.runtime / 'child.pid').read_text())
            return fields if fields and int(fields[2]) == pid and int(fields[4]) > 0 else None
        return self.wait_for(criterion)

    def stop(self):
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(self.proc.pid, signal.SIGKILL)
                self.proc.wait()
                raise AssertionError('Supervisor failed to stop its process group')

    def test_clean_stop_reaps_child_and_removes_runtime_records(self):
        self.start()
        pid = int(self.ready()[2])
        self.stop()
        self.assertEqual(self.proc.returncode, 0)
        for name in ('child.pid', 'supervisor.pid', 'health'):
            self.assertFalse((self.runtime / name).exists())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_second_supervisor_cannot_replace_the_running_instance(self):
        self.start()
        old = self.ready()
        result = subprocess.run(self.command, env=self.env, capture_output=True, text=True, timeout=2)
        self.assertEqual(result.returncode, 0)
        self.assertIn('already-running', result.stdout)
        self.assertEqual((self.runtime / 'supervisor.pid').read_text().strip(), str(self.proc.pid))
        self.assertEqual((self.runtime / 'child.pid').read_text().strip(), old[2])
        self.assertEqual((self.runtime / 'starts').read_text(), '1')

    def recovered(self, old):
        def criterion():
            fields = self.health()
            return fields if fields and fields[1] != old[1] and fields[2] != old[2] else None
        value = self.wait_for(criterion)
        self.assertEqual(value[5], 'READY_LOCAL')
        self.assertIsNone(self.proc.poll())

    def test_killed_child_is_restarted(self):
        self.start()
        old = self.ready()
        os.kill(int(old[2]), signal.SIGKILL)
        self.recovered(old)

    def test_stopped_child_with_live_pid_is_detected(self):
        self.start()
        old = self.ready()
        os.kill(int(old[2]), signal.SIGSTOP)
        os.kill(int(old[2]), 0)
        self.recovered(old)
        self.assertIn('presentation-stalled', self.log.read_text())

    def test_fresh_timestamp_without_new_frame_is_not_healthy(self):
        self.start()
        old = self.ready()
        (self.runtime / 'freeze-counter').touch()
        self.recovered(old)
        self.assertIn('presentation-stalled', self.log.read_text())

    def test_bounded_restarts_and_backoff(self):
        self.start('exit')
        self.proc.wait(timeout=5)
        self.assertEqual(self.proc.returncode, 1)
        self.assertEqual((self.runtime / 'starts').read_text(), '3')
        log = self.log.read_text()
        self.assertIn('backoff_ms=100', log)
        self.assertIn('backoff_ms=200', log)
        self.assertIn('give-up', log)

    def test_wrong_generation_never_satisfies_startup(self):
        self.start('wrong-token')
        self.proc.wait(timeout=5)
        self.assertEqual(self.proc.returncode, 1)
        self.assertIn('startup-timeout', self.log.read_text())

    def test_rendered_error_is_responsive_but_not_operational_ready(self):
        self.start('diagnostic')
        self.assertEqual(self.ready()[5], 'ERROR_RECOVERABLE')
        time.sleep(0.7)
        self.assertEqual((self.runtime / 'starts').read_text(), '1')
        self.assertIsNone(self.proc.poll())


if __name__ == '__main__':
    unittest.main()
