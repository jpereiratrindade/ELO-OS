#!/usr/bin/env python3
"""Exercise local Wi-Fi setup in a temporary /etc with a real PTY and PSK tool."""
import hashlib
import os
from pathlib import Path
import pty
import select
import shutil
import subprocess
import tempfile
import termios
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'board/elo/pi5-client/rootfs-overlay/usr/bin/elo-wifi-connect'


@unittest.skipUnless(shutil.which('wpa_passphrase'), 'requires native wpa_passphrase')
class WifiSetupTest(unittest.TestCase):
    def run_setup(self, ssid, password, country='BR'):
        with tempfile.TemporaryDirectory(prefix='elo-wifi-test-') as temp:
            base = Path(temp)
            (base / 'etc/init.d').mkdir(parents=True)
            (base / 'bin').mkdir()
            fake_id = base / 'bin/id'
            fake_id.write_text('#!/bin/sh\necho 0\n')
            fake_id.chmod(0o755)
            service = base / 'etc/init.d/S41elo-wifi'
            service.write_text('#!/bin/sh\nprintf "%s\\n" "$1" > "' + str(base / 'service-call') + '"\n')
            service.chmod(0o755)
            master, slave = pty.openpty()
            # Redirect filesystem locations only; execute the production logic.
            source = SCRIPT.read_text().replace('/etc/', str(base / 'etc') + '/')
            source = source.replace('/dev/tty', os.ttyname(slave))
            script = base / 'setup.sh'
            script.write_text(source)
            env = {**os.environ, 'PATH': str(base / 'bin') + ':' + os.environ['PATH']}
            proc = subprocess.Popen(['sh', str(script), country, ssid], stdin=slave,
                                    stdout=slave, stderr=slave, env=env)
            output = b''
            sent = False
            deadline = time.monotonic() + 10
            try:
                while time.monotonic() < deadline:
                    if select.select([master], [], [], 0.05)[0]:
                        output += os.read(master, 65536)
                    if not sent and b'Senha Wi-Fi' in output:
                        # Wait for echo to be disabled before emulating typing.
                        if not termios.tcgetattr(slave)[3] & termios.ECHO:
                            os.write(master, password.encode() + b'\n')
                            sent = True
                    if proc.poll() is not None:
                        while select.select([master], [], [], 0)[0]:
                            output += os.read(master, 65536)
                        break
                else:
                    self.fail('Wi-Fi setup timed out')
                self.assertTrue(termios.tcgetattr(slave)[3] & termios.ECHO)
                config = base / 'etc/elo-wifi.conf'
                data = config.read_text() if config.exists() else None
                mode = config.stat().st_mode & 0o777 if config.exists() else None
                service_call = (base / 'service-call').read_text() if (base / 'service-call').exists() else None
                self.assertFalse(list((base / 'etc').glob('.elo-wifi.*')))
                return proc.returncode, output.decode(errors='replace'), data, mode, service_call
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.wait()
                os.close(master)
                os.close(slave)

    def test_secret_hidden_and_real_derived_key(self):
        password = 'Local-test-secret-9284'
        for ssid in ('Test network', 'Network "quoted"', 'Network\nwith newline'):
            with self.subTest(ssid=ssid):
                code, output, data, mode, service = self.run_setup(ssid, password)
                self.assertEqual(code, 0, output)
                self.assertNotIn(password, output)
                self.assertNotIn(password, data)
                self.assertNotIn('#psk', data)
                expected = hashlib.pbkdf2_hmac('sha1', password.encode(), ssid.encode(), 4096, 32).hex()
                self.assertIn('psk=' + expected, data)
                self.assertIn('ssid=' + ssid.encode().hex(), data)
                self.assertEqual(mode, 0o600)
                self.assertEqual(service, 'restart\n')

    def test_short_password_rejected_without_configuration(self):
        code, output, data, _, service = self.run_setup('Test', 'short')
        self.assertEqual(code, 2, output)
        self.assertIsNone(data)
        self.assertIsNone(service)

    def test_invalid_country_rejected(self):
        code, output, data, _, service = self.run_setup('Test', '', country='invalid')
        self.assertEqual(code, 2, output)
        self.assertIsNone(data)
        self.assertIsNone(service)


if __name__ == '__main__':
    unittest.main()
