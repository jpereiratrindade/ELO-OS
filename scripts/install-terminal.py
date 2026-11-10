#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Provision PC user autostart or a mounted Pi 5 rootfs; never flashes a disk."""
import argparse
import hashlib
import getpass
import re
import stat
import os
from pathlib import Path
import shlex
import ssl
import subprocess
import tempfile
import time
from urllib.parse import urlsplit

from elo_content import activate, encoded, read_active, sync_dir
from elo_server import terminal_token

ROOT = Path(__file__).resolve().parents[1]


def unit_argument(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%').replace('$', '$$') + '"'


def wifi_configuration(country, ssid, password):
    if not re.fullmatch(r'[A-Z]{2}', country):
        raise ValueError('Wi-Fi country must have two uppercase letters')
    ssid_bytes = ssid.encode('utf-8')
    if not 1 <= len(ssid_bytes) <= 32:
        raise ValueError('Wi-Fi SSID must have 1 to 32 UTF-8 bytes')
    if not 8 <= len(password) <= 63 or any(ord(c) < 32 or ord(c) > 126 for c in password):
        raise ValueError('Wi-Fi password must have 8 to 63 printable ASCII characters')
    key = hashlib.pbkdf2_hmac('sha1', password.encode('ascii'), ssid_bytes, 4096, 32).hex()
    return (f'country={country}\nctrl_interface=/run/wpa_supplicant\nupdate_config=0\n'
            f'network={{\n    ssid={ssid_bytes.hex()}\n    psk={key}\n    key_mgmt=WPA-PSK\n}}\n').encode()


def read_wifi_password(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise ValueError('Wi-Fi password file must be a private regular file (0600)')
        data = stream.read(66)
    return data.removesuffix(b'\n').removesuffix(b'\r').decode('ascii')


def provision(platform, destination, server, credential, ca=None, seed=None, binary=None, wifi=None, ssh_keys=()):
    if platform not in ('pc', 'pi5'): raise ValueError('Unsupported platform')
    if wifi is not None and platform != 'pi5': raise ValueError('Wi-Fi provisioning applies only to Pi')
    authorized = []
    for key_file in ssh_keys:
        key = Path(key_file).read_text().strip()
        if '\n' in key or not key.startswith(('ssh-ed25519 ', 'ssh-rsa ', 'ecdsa-sha2-')):
            raise ValueError('Use a plain SSH public key file, never a private key')
        if subprocess.run(['ssh-keygen', '-l', '-f', str(key_file)], capture_output=True).returncode:
            raise ValueError('Invalid SSH public key')
        authorized.append(key)
    if authorized and platform != 'pi5': raise ValueError('SSH provisioning applies only to Pi')
    endpoint = urlsplit(server)
    if (any(c.isspace() or ord(c) < 32 for c in server) or endpoint.scheme != 'https'
            or not endpoint.hostname or endpoint.username or endpoint.password
            or endpoint.query or endpoint.fragment or endpoint.path != '/v1/presentation'):
        raise ValueError('Use HTTPS URL ending in /v1/presentation, without credentials or query')
    endpoint.port  # Validate port before making any changes.
    secret = terminal_token(credential)
    certificate = Path(ca).read_bytes() if ca else None
    if certificate:
        ssl.create_default_context(cadata=certificate.decode('ascii'))
    # Validate seed before touching installation. Keep destination cache if already active.
    seed_payload = encoded(read_active(seed)) if seed else None
    destination = Path(destination).resolve()
    if platform == 'pc':
        binary = Path(binary or ROOT / 'build/client-fedora/elo-client').resolve()
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise ValueError('Build native client first: scripts/run-client.sh')
        config = destination / '.config/elo-terminal'
        cache = destination / '.local/share/elo-client/content'
        library = destination / '.local/share/elo-terminal/bin'
    else:
        if destination == Path('/') or not (destination / 'etc/os-release').is_file():
            raise ValueError('Pi target must be a mounted rootfs directory, never host /')
        if not (destination / 'usr/bin/elo-client').is_file():
            raise ValueError('Pi rootfs must include elo-client')
        if endpoint.hostname in ('localhost', '127.0.0.1', '::1'):
            raise ValueError('Pi needs server LAN address or DNS name, not loopback')
        existing_keys = destination / 'root/.ssh/authorized_keys'
        if not authorized and (not existing_keys.is_file() or existing_keys.is_symlink() or not existing_keys.stat().st_size):
            raise ValueError('Pi requires --ssh-authorized-key for maintenance without keyboard')
        config = destination / 'etc/elo-terminal'
        cache = destination / 'var/lib/elo-client/content'
        library = destination / 'usr/bin'
        startup_content = read_active(seed) if seed else read_active(cache)
        if startup_content.get('version') != '4' or not startup_content.get('exposure_seconds'):
            raise ValueError('Pi needs automatic initial content: --seed-content from configured PC cache')
    for path in (config, cache):
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o700)
    # server.url is activation marker. Write it last on first provisioning.
    def write(path, data, mode=0o600):
        fd, temporary = tempfile.mkstemp(prefix='.terminal-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.chmod(temporary, mode)
            os.replace(temporary, path)
            sync_dir(path.parent)
        finally:
            Path(temporary).unlink(missing_ok=True)
    write(config / 'terminal.token', secret + b'\n')
    if certificate: write(config / 'ca.pem', certificate)
    else: (config / 'ca.pem').unlink(missing_ok=True)
    if seed_payload and not (cache / 'active.json').exists():
        with tempfile.NamedTemporaryFile() as source:
            source.write(seed_payload); source.flush()
            activate(cache, Path(source.name), len(seed_payload), hashlib.sha256(seed_payload).hexdigest())
    library.mkdir(parents=True, exist_ok=True)
    write(library / 'elo-terminal', (ROOT / 'package/elo-client/src/terminal.sh').read_bytes(), 0o755)
    write(library / 'elo-client-supervisor', (ROOT / 'board/elo/qemu-gui/rootfs-overlay/usr/bin/elo-client-supervisor').read_bytes(), 0o755)
    if platform == 'pc':
        write(library / 'elo-client', binary.read_bytes(), 0o755)
        launch = ['#!/bin/sh', 'set -eu']
        for key, value in {'ELO_TERMINAL_CONFIG': config, 'ELO_CONTENT_DIR': cache,
                           'ELO_CLIENT_BIN': library / 'elo-client', 'QT_QUICK_BACKEND': 'software'}.items():
            launch.append(f'export {key}={shlex.quote(str(value))}')
        launch += ['export ELO_RUNTIME_DIR="${XDG_RUNTIME_DIR:?Graphical session required}/elo-terminal"',
                   'exec ' + shlex.quote(str(library / 'elo-client-supervisor')) + ' ' + shlex.quote(str(library / 'elo-terminal'))]
        write(library / 'launch', ('\n'.join(launch) + '\n').encode(), 0o755)
        units = destination / '.config/systemd/user'
        units.mkdir(parents=True, exist_ok=True)
        unit = '\n'.join(['[Unit]', 'Description=ELO unattended terminal',
            'After=graphical-session.target', 'PartOf=graphical-session.target',
            'StartLimitIntervalSec=300', 'StartLimitBurst=3', '', '[Service]',
            'ExecStart=' + unit_argument(library / 'launch'), 'Restart=on-failure', 'RestartSec=15',
            'TimeoutStopSec=8', 'KillMode=control-group', 'UMask=0077', 'NoNewPrivileges=yes',
            '', '[Install]', 'WantedBy=graphical-session.target', ''])
        write(units / 'elo-client.service', unit.encode())
    else:
        write(library / 'elo-client-start', (ROOT / 'board/elo/pi5-client/rootfs-overlay/usr/bin/elo-client-start').read_bytes(), 0o755)
        write(destination / 'etc/init.d/S50elo-client', (ROOT / 'board/elo/pi5-client/rootfs-overlay/etc/init.d/S50elo-client').read_bytes(), 0o755)
    if platform == 'pi5':
        write(destination / 'etc/init.d/S41elo-wifi', (ROOT / 'board/elo/pi5-client/rootfs-overlay/etc/init.d/S41elo-wifi').read_bytes(), 0o755)
        if wifi is not None: write(destination / 'etc/elo-wifi.conf', wifi)
        clock = destination / 'var/lib/elo-time'
        clock.mkdir(parents=True, exist_ok=True); clock.chmod(0o700)
        write(clock / 'last-good-utc', (str(int(time.time())) + '\n').encode())
        if authorized:
            ssh = destination / 'root/.ssh'
            ssh.mkdir(parents=True, exist_ok=True); ssh.chmod(0o700)
            write(ssh / 'authorized_keys', ('\n'.join(authorized) + '\n').encode())
    write(config / 'server.url', (server + '\n').encode())
    return config, cache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=('pc', 'pi5'), required=True)
    parser.add_argument('--root', type=Path, help='PC user home or mounted Pi rootfs')
    parser.add_argument('--server', required=True)
    parser.add_argument('--token-file', type=Path, required=True)
    parser.add_argument('--ca-file', type=Path)
    parser.add_argument('--seed-content', type=Path)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--ssh-authorized-key', action='append', type=Path, default=[])
    parser.add_argument('--wifi-ssid', help='Pi WPA2-Personal network name; password prompted without echo')
    parser.add_argument('--wifi-country', default='BR')
    parser.add_argument('--wifi-password-file', type=Path, help='Optional private 0600 file for automation')
    parser.add_argument('--activate', action='store_true', help='PC only: enable graphical-session autostart')
    parser.add_argument('--start', action='store_true', help='PC only: also open client now')
    args = parser.parse_args()
    if args.platform == 'pi5' and (not args.root or args.activate or args.start):
        parser.error('Pi requires --root; activation occurs on its next boot')
    if args.start and not args.activate:
        parser.error('--start requires --activate')
    destination = args.root or Path.home()
    if args.activate and destination.resolve() != Path.home().resolve():
        parser.error('--activate applies only to current user home')
    if args.wifi_password_file and args.wifi_ssid is None:
        parser.error('--wifi-password-file requires --wifi-ssid')
    wifi = None
    if args.wifi_ssid is not None:
        if args.platform != 'pi5': parser.error('Wi-Fi setup applies only to Pi')
        if args.wifi_password_file:
            password = read_wifi_password(args.wifi_password_file)
        else:
            if not os.isatty(0): parser.error('Use a terminal for hidden password entry, or --wifi-password-file')
            password = getpass.getpass('Senha Wi-Fi (não será exibida): ')
        wifi = wifi_configuration(args.wifi_country, args.wifi_ssid, password)
        del password
    os.umask(0o077)
    config, cache = provision(args.platform, destination, args.server, args.token_file,
                              args.ca_file, args.seed_content, args.binary, wifi, args.ssh_authorized_key)
    if args.activate:
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', '--user', 'enable', 'elo-client.service'], check=True)
    if args.start:
        names = [name for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_RUNTIME_DIR') if os.environ.get(name)]
        if names: subprocess.run(['systemctl', '--user', 'import-environment', *names], check=True)
        subprocess.run(['systemctl', '--user', 'restart', 'elo-client.service'], check=True)
    print('Terminal provisioned:', args.platform)
    print('Configuration:', config)
    print('Persistent cache:', cache)


if __name__ == '__main__':
    main()
