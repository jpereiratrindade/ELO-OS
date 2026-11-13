#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Install and start the local HTTPS distribution daemon as a systemd user service."""
import argparse
from pathlib import Path
import shutil
import subprocess
import os
import re
import ipaddress
import tempfile

from elo_server import envelope, terminal_token
from elo_studio_assets import publication_actions, versioned_assets


def quoted(value):
    value = str(value)
    if any(c in value for c in '\n\r\0'):
        raise ValueError('Unsupported unit argument')
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%').replace('$', '$$') + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--variant', action='append', required=True)
    parser.add_argument('--port', type=int, default=8443)
    parser.add_argument('--host', default='127.0.0.1', help='Listen address; 0.0.0.0 enables IPv4 LAN and localhost')
    parser.add_argument('--tls-name', action='append', default=[], help='Additional DNS name or IP in local certificate')
    parser.add_argument('--renew-certificate', action='store_true', help='Reissue existing local certificate with requested names')
    parser.add_argument('--elo-root', type=Path, default=Path(__file__).resolve().parents[2] / 'elo')
    parser.add_argument('--enable-ingest', action='store_true', help='Enable dedicated private intake spool; valid uploads remain quarantined')
    parser.add_argument('--ingest-producer', help='Operator-assigned Sister-Studio installation ID (required with --enable-ingest)')
    args = parser.parse_args()
    if args.enable_ingest != bool(args.ingest_producer):
        parser.error('--enable-ingest and --ingest-producer must be supplied together')
    if args.ingest_producer and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', args.ingest_producer):
        parser.error('Invalid ingest producer identity')
    ipaddress.ip_address(args.host)
    names = ['DNS:localhost', 'IP:127.0.0.1']
    for name in args.tls_name:
        try: names.append('IP:' + str(ipaddress.ip_address(name)))
        except ValueError:
            if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?', name):
                raise ValueError('Invalid TLS DNS name')
            names.append('DNS:' + name)
    os.umask(0o077)
    source = args.bundle.absolute()  # Preserve current symlink for future publication changes.
    envelope(source, args.variant)
    home = Path.home()
    private = home / '.config/elo-distribution'
    library = home / '.local/share/elo-distribution/lib'
    units = home / '.config/systemd/user'
    for directory in (private, library, units):
        directory.mkdir(parents=True, exist_ok=True)
    private.chmod(0o700)
    library.chmod(0o700)
    token = private / 'terminal.token'
    terminal_token(token, create=True)
    admin_token = private / 'admin.token'
    terminal_token(admin_token, create=True)
    state = home / '.local/share/elo-distribution/state'
    state.mkdir(parents=True, exist_ok=True)
    state.chmod(0o700)
    key, certificate = private / 'server.key', private / 'server.crt'
    if key.exists() != certificate.exists():
        raise ValueError('Incomplete existing TLS material; repair before install')
    if not key.exists():
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:3072', '-nodes', '-days', '365',
                        '-subj', '/CN=localhost', '-addext', 'subjectAltName=' + ','.join(dict.fromkeys(names)),
                        '-keyout', str(key), '-out', str(certificate)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif args.renew_certificate:
        fd, temporary = tempfile.mkstemp(prefix='.server-cert-', dir=private)
        os.close(fd)
        try:
            subprocess.run(['openssl', 'req', '-new', '-x509', '-key', str(key), '-days', '365',
                '-subj', '/CN=localhost', '-addext', 'subjectAltName=' + ','.join(dict.fromkeys(names)),
                '-out', temporary], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.chmod(temporary, 0o600)
            os.replace(temporary, certificate)
        finally:
            Path(temporary).unlink(missing_ok=True)
    elif args.tls_name:
        for name in args.tls_name:
            try: ipaddress.ip_address(name); option = '-checkip'
            except ValueError: option = '-checkhost'
            if subprocess.run(['openssl', 'x509', '-in', str(certificate), '-noout', option, name],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
                raise ValueError('Certificate lacks requested name; use --renew-certificate')
    for name in ('elo_server.py', 'elo_import.py', 'elo_content.py', 'elo_panel.py', 'elo_receipts.py', 'elo_terminals.py', 'elo_control.py', 'elo_telemetry.py', 'elo_ingest.py', 'elo_consumable.py'):
        shutil.copyfile(Path(__file__).parent / name, library / name)
    web = library / 'web'
    shutil.copytree(Path(__file__).resolve().parents[1] / 'web/distribution', web, dirs_exist_ok=True)
    icons = home / '.local/share/icons/hicolor/scalable/apps'
    icons.mkdir(parents=True, exist_ok=True)
    for name in ('elo', 'elo-os'):
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'assets/identity' / (name + '.svg'), icons / (name + '.svg'))
        (icons / (name + '.svg')).chmod(0o644)
    applications = home / '.local/share/applications'
    applications.mkdir(parents=True, exist_ok=True)
    desktop = applications / 'elo-management.desktop'
    desktop.write_text('[Desktop Entry]\nType=Application\nName=ELO · Gerenciamento\n'
        'Comment=Curadoria editorial, distribuição e acompanhamento de totens\n'
        f'Exec=xdg-open https://localhost:{args.port}/\nIcon=elo\nTerminal=false\nCategories=Education;\n')
    desktop.chmod(0o644)
    studio = web / 'studio'
    studio.mkdir(exist_ok=True)
    elo = args.elo_root.resolve()
    executable = elo / 'build/apps/elo-admin/elo-admin'
    if not executable.is_file():
        raise ValueError('Build elo-admin in --elo-root before installing panel')
    for name in ('index.html', 'app.css', 'app.js'):
        shutil.copyfile(elo / 'web/admin' / name, studio / name)
    html = (studio / 'index.html').read_text()
    html = re.sub(r'^.*<link[^>]+https://fonts[^>]*>.*\n', '', html, flags=re.MULTILINE)
    html = html.replace('Plano editorial soberano desacoplado do runtime · C++26 · Raspberry Pi 5',
                        'Conteúdo editorial · publicação para terminais')
    html = html.replace('<div class="header-right">', '<div class="header-right"><a class="distribution-link" href="/">← Distribuição</a>')
    html = html.replace('</head>', '<link rel="icon" type="image/svg+xml" href="/elo.svg"><link rel="stylesheet" href="/studio/theme.css"></head>')
    if 'aria-label="Princípios de desenvolvimento"' not in html:
        html = html.replace('</body>', (web / 'principles.html').read_text() + '</body>')
    html = html.replace('Publicar no Totem', 'Publicar versão ELO').replace('Validar Catálogo (C++)', 'Validar catálogo')
    html = html.replace('ESTADO EDITORIAL CONSTITUCIONAL (ELO-ADMIN-001)', 'ESTADO DA PUBLICAÇÃO').replace('ACTIVE (No Totem)', 'PUBLICADA NO ELO')
    html = html.replace('ELO Content Studio · Arquitetura Constitucional ELO-ADMIN-001 & ELO-PUBLISHING-001 · GPL-3.0', 'ELO · Curadoria e distribuição de conteúdo')
    (studio / 'index.html').write_text(versioned_assets(html))
    css = (studio / 'app.css').read_text()
    css = css.replace('.form-hint {\n  font-size: 0.7rem;\n.form-row-3', '.form-hint {\n  font-size: 0.7rem;\n}\n.form-row-3')
    (studio / 'app.css').write_text(css)
    javascript = publication_actions((studio / 'app.js').read_text()).replace('ACTIVE (No Totem)', 'PUBLICADA NO ELO')
    (studio / 'app.js').write_text(javascript)
    launch = library / 'launch_studio.py'
    launch.write_text('import os\nfrom pathlib import Path\n'
        + f'os.environ["ELO_ADMIN_TOKEN"] = Path({str(admin_token)!r}).read_text().strip()\n'
        + f'os.environ["ELO_CONTENT_DIR"] = {str(source.parent)!r}\n'
        + f'os.environ["ELO_WEB_ROOT"] = {str(studio)!r}\n'
        + 'os.environ["ELO_ADMIN_PORT"] = "18080"\n'
        + f'os.execv({str(executable)!r}, [{str(executable)!r}])\n')
    studio_unit = units / 'elo-studio.service'
    studio_unit.write_text('\n'.join([
        '[Unit]', 'Description=ELO editorial Studio loopback backend', '', '[Service]',
        'ExecStart=/usr/bin/python3 -B -s -E ' + quoted(launch),
        'Restart=on-failure', 'RestartSec=5', 'UMask=0077', 'NoNewPrivileges=yes',
        'MemoryMax=768M', 'TasksMax=64', 'LimitNOFILE=256',
        'PrivateTmp=yes', 'ProtectSystem=strict', 'ProtectHome=read-only',
        'ReadWritePaths=' + quoted(source.parent),
        '', '[Install]', 'WantedBy=default.target', '']))
    command = ['/usr/bin/python3' , '-B', '-s', '-E', '-u', library / 'elo_server.py', '--bundle', source,
               '--token-file', token, '--cert', certificate, '--key', key, '--host', args.host, '--port', str(args.port)]
    command += ['--admin-token-file', admin_token, '--selection-file', state / 'selection.json',
                '--web-root', web, '--studio-port', '18080']
    if args.enable_ingest:
        ingest_token = private / 'ingest.token'
        terminal_token(ingest_token, create=True)
        ingest_root = state / 'ingest'
        ingest_root.mkdir(exist_ok=True, mode=0o700)
        command += ['--ingest-token-file', ingest_token, '--ingest-root', ingest_root,
                    '--ingest-producer', args.ingest_producer]
    for variant in args.variant:
        command += ['--variant', variant]
    unit = '\n'.join([
        '[Unit]', 'Description=ELO HTTPS content distribution and editorial gateway',
        'After=network.target elo-studio.service', 'Wants=elo-studio.service', '', '[Service]', 'Type=simple',
        'ExecStart=' + ' '.join(quoted(value) for value in command),
        'Restart=on-failure', 'RestartSec=5', 'UMask=0077',
        'MemoryMax=512M', 'TasksMax=128', 'LimitNOFILE=512',
        'NoNewPrivileges=yes', 'PrivateTmp=yes', 'ProtectSystem=strict',
        'ProtectHome=read-only', 'RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX',
        'ReadOnlyPaths=' + quoted(source.parent),
        'ReadWritePaths=' + quoted(state),
        'StandardOutput=journal', 'StandardError=journal',
        '', '[Install]', 'WantedBy=default.target', ''])
    destination = units / 'elo-content.service'
    destination.write_text(unit)
    subprocess.run(['systemd-analyze', '--user', 'verify', str(destination), str(studio_unit)], check=True)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'enable', 'elo-content.service', 'elo-studio.service'], check=True)
    subprocess.run(['systemctl', '--user', 'restart', 'elo-studio.service', 'elo-content.service'], check=True)
    print('Installed: elo-content.service')
    print(f'Endpoint: https://localhost:{args.port}/v1/presentation')
    print(f'Terminal credential: {token}')
    print(f'Local trust certificate: {certificate}')


if __name__ == '__main__':
    main()
