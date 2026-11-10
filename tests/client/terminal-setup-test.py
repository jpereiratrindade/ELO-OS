#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
import hashlib
import importlib.util
import os
import pty
import select
import termios
import time
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from elo_content import activate, encoded, read_active
spec = importlib.util.spec_from_file_location('terminal_setup', ROOT / 'scripts/install-terminal.py')
setup = importlib.util.module_from_spec(spec); spec.loader.exec_module(setup)


class TerminalSetupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.token = self.base / 'token'; self.token.write_text('t' * 43); self.token.chmod(0o600)
        self.binary = self.base / 'fake-client'
        self.binary.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n'); self.binary.chmod(0o755)
        self.server = 'https://elo.test:8443/v1/presentation'
        self.ssh_key = self.base / 'test-ssh'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(self.ssh_key)], check=True)
        self.ssh_public = Path(str(self.ssh_key)+'.pub')

    def test_pc_install_and_launcher_forward_literal_arguments(self):
        home = self.base / "home with space $money %value 'quote"
        config, cache = setup.provision('pc', home, self.server, self.token, binary=self.binary)
        self.assertEqual((config / 'terminal.token').stat().st_mode & 0o777, 0o600)
        terminal = home / '.local/share/elo-terminal/bin/elo-terminal'
        result = subprocess.run([str(terminal), '--health-file', '/run/private health'], capture_output=True, text=True,
            env=dict(os.environ, ELO_TERMINAL_CONFIG=str(config), ELO_CONTENT_DIR=str(cache),
                     ELO_CLIENT_BIN=str(home / '.local/share/elo-terminal/bin/elo-client')), check=True)
        self.assertEqual(result.stdout.splitlines(), ['--fullscreen', '--content-dir', str(cache), '--server',
            self.server, '--token-file', str(config / 'terminal.token'), '--health-file', '/run/private health'])
        subprocess.run(['sh', '-n', str(terminal.parent / 'launch')], check=True)
        unit = (home / '.config/systemd/user/elo-client.service').read_text()
        self.assertIn('WantedBy=graphical-session.target', unit)
        self.assertIn('KillMode=control-group', unit)
        self.assertNotIn('t' * 43, unit)
        self.assertIn('%%value', unit)
        self.assertIn('$$money', unit)

    def test_invalid_url_and_token_never_activate(self):
        for url in ('http://elo.test/v1/presentation', 'https://user:pass@elo.test/v1/presentation',
                    'https://elo.test/v1/presentation?token=x', 'https://elo.test/v1/presentation\n',
                    'https://elo.test:invalid/v1/presentation'):
            with self.assertRaises(ValueError): setup.provision('pc', self.base / 'home', url, self.token, binary=self.binary)
        self.assertFalse((self.base / 'home').exists())
        self.token.chmod(0o644)
        with self.assertRaises(ValueError): setup.provision('pc', self.base / 'home', self.server, self.token, binary=self.binary)

    def test_seed_validated_and_existing_cache_preserved(self):
        source = self.base / 'seed.json'
        payload = encoded({'schema': 1, 'id': 'test', 'name': 'Automático', 'version': '4', 'exposure_seconds': 15,
            'pages': [{'title': 'Página', 'body': 'Sem mouse.'}]})
        source.write_bytes(payload)
        seed = self.base / 'seed'; activate(seed, source, len(payload), hashlib.sha256(payload).hexdigest())
        home = self.base / 'home'
        _, cache = setup.provision('pc', home, self.server, self.token, seed=seed, binary=self.binary)
        self.assertEqual(read_active(cache)['exposure_seconds'], 15)
        pointer = (cache / 'active.json').read_bytes()
        setup.provision('pc', home, self.server, self.token, seed=seed, binary=self.binary)
        self.assertEqual((cache / 'active.json').read_bytes(), pointer)
        (seed / 'active.json').write_text('{}')
        with self.assertRaises(ValueError): setup.provision('pc', self.base / 'bad', self.server, self.token, seed=seed, binary=self.binary)
        self.assertFalse((self.base / 'bad').exists())

    def test_wifi_derived_key_and_password_file_privacy(self):
        secret = 'Local-password-123'
        ssid = 'Rede "Pampa"'
        data = setup.wifi_configuration('BR', ssid, secret)
        expected = hashlib.pbkdf2_hmac('sha1', secret.encode(), ssid.encode(), 4096, 32).hex()
        self.assertIn(('psk=' + expected).encode(), data)
        self.assertIn(('ssid=' + ssid.encode().hex()).encode(), data)
        self.assertNotIn(secret.encode(), data)
        self.assertNotIn(b'#psk', data)
        for country, name, password in [('BRA', ssid, secret), ('BR', '', secret),
                ('BR', 'x' * 33, secret), ('BR', ssid, 'short'), ('BR', ssid, 'bad\npassword')]:
            with self.assertRaises(ValueError): setup.wifi_configuration(country, name, password)
        path = self.base / 'wifi-password'; path.write_text(secret + '\n'); path.chmod(0o600)
        self.assertEqual(setup.read_wifi_password(path), secret)
        path.chmod(0o644)
        with self.assertRaises(ValueError): setup.read_wifi_password(path)
        link = self.base / 'wifi-link'; link.symlink_to(path)
        with self.assertRaises(OSError): setup.read_wifi_password(link)

    def test_wifi_password_prompt_never_echoes_secret(self):
        root = self.base / 'prompt-root'
        (root / 'etc/init.d').mkdir(parents=True)
        (root / 'etc/os-release').write_text('ID=elo-os\n')
        (root / 'usr/bin').mkdir(parents=True)
        (root / 'usr/bin/elo-client').write_bytes(self.binary.read_bytes())
        source = self.base / 'prompt.json'
        payload = encoded({'schema': 1, 'id': 'pi', 'name': 'Inicial', 'version': '4',
            'exposure_seconds': 15, 'pages': [{'title': 'Pronto', 'body': 'Offline.'}]})
        source.write_bytes(payload)
        seed = self.base / 'prompt-content'
        activate(seed, source, len(payload), hashlib.sha256(payload).hexdigest())
        secret = 'Hidden-prompt-9372'
        master, slave = pty.openpty()
        proc = subprocess.Popen([sys.executable, str(ROOT / 'scripts/install-terminal.py'),
            '--platform', 'pi5', '--root', str(root), '--server', self.server,
            '--token-file', str(self.token), '--seed-content', str(seed), '--wifi-ssid', 'Rede teste',
            '--ssh-authorized-key', str(self.ssh_public)],
            stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
        output = b''
        sent = False
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if select.select([master], [], [], .05)[0]: output += os.read(master, 65536)
                if not sent and b'Senha Wi-Fi' in output and not termios.tcgetattr(slave)[3] & termios.ECHO:
                    os.write(master, (secret + '\n').encode()); sent = True
                if proc.poll() is not None:
                    while select.select([master], [], [], 0)[0]: output += os.read(master, 65536)
                    break
            else: self.fail('Hidden Wi-Fi prompt timed out')
            self.assertEqual(proc.returncode, 0, output.decode(errors='replace'))
            self.assertTrue(sent)
            self.assertNotIn(secret.encode(), output)
            self.assertNotIn(secret.encode(), (root / 'etc/elo-wifi.conf').read_bytes())
        finally:
            if proc.poll() is None: proc.kill()
            proc.wait(); os.close(master); os.close(slave)

    def test_incremental_build_refreshes_pi_boot_parameters(self):
        images = self.base / 'images'
        (images / 'rpi-firmware').mkdir(parents=True)
        command_line = images / 'rpi-firmware/cmdline.txt'
        command_line.write_text('old cached firmware command line\n')
        subprocess.run(['bash', str(ROOT / 'board/elo/pi5-client/post-build.sh')], check=True,
                       env=dict(os.environ, BINARIES_DIR=str(images)))
        self.assertIn('consoleblank=0', command_line.read_text().split())
        self.assertEqual((images / 'rpi-firmware/config.txt').read_bytes(),
                         (ROOT / 'board/elo/pi5-client/config.txt').read_bytes())

    def test_clock_floor_only_advances_without_setting_host_clock(self):
        state = self.base / 'time'; state.mkdir()
        (state / 'last-good-utc').write_text('1800000000\n')
        commands = self.base / 'commands'; commands.mkdir()
        calls = self.base / 'date-calls'
        fake = commands / 'date'
        fake.write_text('#!/bin/sh\nif [ "$2" = +%s ]; then echo 100; else printf "%s\n" "$*" >> '+str(calls)+'; fi\n')
        fake.chmod(0o755)
        source = (ROOT / 'board/elo/pi5-client/rootfs-overlay/etc/init.d/S42elo-clock').read_text()
        path = self.base / 'clock.sh';path.write_text(source.replace('/var/lib/elo-time', str(state)))
        subprocess.run(['sh', str(path), 'start'], check=True,
            env=dict(os.environ, PATH=str(commands)+os.pathsep+os.environ['PATH']))
        self.assertIn('@1800000000', calls.read_text())

    def test_unconfigured_pi_boot_does_not_start_client(self):
        script = ROOT / 'board/elo/pi5-client/rootfs-overlay/etc/init.d/S50elo-client'
        source = script.read_text().replace('/etc/elo-terminal', str(self.base / 'unconfigured'))
        path = self.base / 'boot.sh'; path.write_text(source)
        result = subprocess.run(['sh', str(path), 'start'], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'')

    def test_pi_target_installs_boot_and_rejects_loopback(self):
        root = self.base / 'pi-root'
        (root / 'etc/init.d').mkdir(parents=True)
        (root / 'etc/os-release').write_text('ID=elo-os\n')
        (root / 'usr/bin').mkdir(parents=True)
        (root / 'usr/bin/elo-client').write_bytes(self.binary.read_bytes())
        with self.assertRaises(ValueError): setup.provision('pi5', root, 'https://localhost:8443/v1/presentation', self.token)
        source = self.base / 'initial.json'
        payload = encoded({'schema': 1, 'id': 'pi', 'name': 'Inicial', 'version': '4',
            'exposure_seconds': 15, 'pages': [{'title': 'Pronto', 'body': 'Mesmo sem rede.'}]})
        source.write_bytes(payload)
        seed = self.base / 'initial-content'
        activate(seed, source, len(payload), hashlib.sha256(payload).hexdigest())
        wifi = setup.wifi_configuration('BR', 'Rede do totem', 'Teste-local-123')
        key = self.base / 'maintenance-key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True)
        config, cache = setup.provision('pi5', root, self.server, self.token, seed=seed, wifi=wifi,
                                       ssh_keys=[Path(str(key)+'.pub')])
        self.assertEqual((root / 'root/.ssh/authorized_keys').stat().st_mode & 0o777, 0o600)
        self.assertEqual((root / 'root/.ssh').stat().st_mode & 0o777, 0o700)
        self.assertNotIn(key.read_text(), (root / 'root/.ssh/authorized_keys').read_text())
        self.assertGreater(int((root / 'var/lib/elo-time/last-good-utc').read_text()), 1704067200)
        self.assertEqual(cache, root / 'var/lib/elo-client/content')
        self.assertNotIn(b'Teste-local-123', (root / 'etc/elo-wifi.conf').read_bytes())
        self.assertEqual((root / 'etc/elo-wifi.conf').stat().st_mode & 0o777, 0o600)
        self.assertEqual(read_active(cache)['exposure_seconds'], 15)
        self.assertTrue((root / 'etc/init.d/S50elo-client').is_file())
        self.assertTrue(os.access(root / 'usr/bin/elo-client-supervisor', os.X_OK))
        self.assertEqual((config / 'server.url').read_text().strip(), self.server)
        with self.assertRaises(ValueError): setup.provision('pi5', Path('/'), self.server, self.token)


if __name__ == '__main__': unittest.main()
