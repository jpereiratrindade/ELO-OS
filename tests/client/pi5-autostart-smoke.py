#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Provision a disposable Pi rootfs and boot on virt ARM64 without NIC or input devices."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import select
import shutil
import subprocess
import sys
import tempfile
import time
from maintenance_fixture import MaintenanceFixture

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from elo_content import activate, encoded, read_active
spec = importlib.util.spec_from_file_location('gui', ROOT / 'tests/client/qemu-gui-smoke.py')
gui = importlib.util.module_from_spec(spec); spec.loader.exec_module(gui)
spec = importlib.util.spec_from_file_location('setup', ROOT / 'scripts/install-terminal.py')
setup = importlib.util.module_from_spec(spec); spec.loader.exec_module(setup)


def main():
    out = Path(os.environ.get('OUTPUT_DIR', ROOT / 'output/pi5-client')).resolve()
    kernel = Path(os.environ.get('QEMU_TEST_KERNEL', ROOT / 'output/toolbox/qemu-aarch64-gui/images/Image')).resolve()
    original = out / 'images/rootfs.ext4'
    assert original.is_file() and kernel.is_file(), 'Build Pi rootfs and virt ARM64 kernel first'
    report = {'status': 'FAIL', 'scope': 'Pi rootfs with generic virt ARM64 kernel; no physical firmware or Wi-Fi test',
              'original_sha256': gui.digest(original), 'network': 'no NIC', 'input': 'no mouse or keyboard devices', 'checks': []}
    proc = qmp = maintenance = None
    maintenance_mode = os.environ.get("ELO_MAINTENANCE_TEST") == "1"
    with tempfile.TemporaryDirectory(prefix='elo-autoboot-') as temporary:
        base = Path(temporary)
        image = base / 'rootfs.ext4'
        subprocess.run(['cp', '--reflink=auto', str(original), str(image)], check=True)
        root = base / 'stage'
        (root / 'etc/init.d').mkdir(parents=True)
        (root / 'etc/os-release').write_text('ID=elo-os\n')
        (root / 'usr/bin').mkdir(parents=True)
        shutil.copyfile(out / 'target/usr/bin/elo-client', root / 'usr/bin/elo-client')
        token = base / 'terminal.token'; token.write_text('t' * 43); token.chmod(0o600)
        source = base / 'presentation.json'
        # The actual editorial JPEG exercises cross-built Qt image decoding too.
        image_content = Path(os.environ.get('ELO_IMAGE_CONTENT_DIR', ROOT / 'build/elo-image-content'))
        picture = read_active(image_content)['pages'][0]
        document = {'schema': 1, 'id': 'autoboot-test', 'name': 'Teste isolado sem entrada', 'version': '4',
            'exposure_seconds': 5, 'pages': [{'title': 'Início automático', 'body': 'Sem servidor, mouse ou teclado.'}, picture]}
        payload = encoded(document); source.write_bytes(payload)
        seed = base / 'seed'
        activate(seed, source, len(payload), hashlib.sha256(payload).hexdigest())
        if maintenance_mode:
            maintenance = MaintenanceFixture(base, payload)
            setup.provision('pi5', root, f'https://10.0.2.2:{maintenance.https.server_port}/v1/presentation',
                            token, ca=maintenance.cert, seed=seed, ssh_keys=[maintenance.public])
            (root / 'etc/chrony.conf').write_text(
                f'server 10.0.2.2 port {maintenance.ntp.getsockname()[1]} iburst minpoll 0 maxpoll 4\n'
                'makestep 0.1 -1\ndriftfile /var/lib/chrony/drift\ncmdport 0\n')
            (root / 'var/lib/elo-time/last-good-utc').write_text(str(int(time.time()) - 86400) + '\n')
            report['network'] = 'isolated user NIC, local NTP/HTTPS fixture'
        else:
            offline_key = base / 'offline-maintenance-key'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(offline_key)], check=True)
            setup.provision('pi5', root, 'https://192.0.2.1:8443/v1/presentation', token, seed=seed,
                            ssh_keys=[base / 'offline-maintenance-key.pub'])
        # Seed only the generated configuration/cache files; preserve built binaries in image.
        commands = []
        for directory in sorted(root.rglob('*')):
            relative = '/' + directory.relative_to(root).as_posix()
            if directory.is_dir():
                commands.append('mkdir ' + relative)
            elif relative not in ('/etc/os-release', '/usr/bin/elo-client'):
                commands += ['rm ' + relative, f'write {directory} {relative}',
                             f'set_inode_field {relative} mode 0{(directory.stat().st_mode & 0o777 | 0o100000):o}']
        instructions = base / 'debugfs.commands'; instructions.write_text('\n'.join(commands) + '\n')
        subprocess.run(['debugfs', '-w', '-f', str(instructions), str(image)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 300
        buffer = b''
        with (out / ('maintenance-qemu.log' if maintenance_mode else 'autostart-qemu.log')).open('wb') as log, (out / ('maintenance-qemu-stderr.log' if maintenance_mode else 'autostart-qemu-stderr.log')).open('wb') as errors:
            def wait_for(pattern):
                nonlocal buffer
                while time.monotonic() < deadline:
                    match = re.search(pattern, buffer)
                    if match:
                        output = buffer[:match.start()]; buffer = buffer[match.end():]
                        return match, output
                    if select.select([proc.stdout], [], [], .2)[0]:
                        chunk = os.read(proc.stdout.fileno(), 65536)
                        if not chunk: raise RuntimeError('QEMU console closed')
                        buffer += chunk; log.write(chunk); log.flush()
                        if b'Kernel panic' in buffer: raise RuntimeError('Kernel panic')
                raise TimeoutError(str(pattern))
            def send(command):
                proc.stdin.write(command.encode() + b'\n'); proc.stdin.flush()
            def command(name, body):
                nonce = secrets.token_hex(8)
                send('{ ' + body + "; }; rc=$?; printf '\\n%s%s:%s\\n' ELO_ " + nonce + ' "$rc"')
                match, output = wait_for(rb'(?m)^ELO_' + nonce.encode() + rb':([0-9]+)\r?$')
                if match[1] != b'0': raise RuntimeError(name + ': ' + output.decode(errors='replace'))
                wait_for(rb'# '); report['checks'].append(name)
                return output.decode(errors='replace')
            def health(page):
                return command('automatic-page-' + str(page),
                    'found=0; for n in $(seq 1 40); do '
                    'if test -s /run/elo-client/health; then '
                    'read -r magic token pid stamp sequence state page digest < /run/elo-client/health; '
                    f'if test "$magic" = ELO_HEALTH_V1 && test "$page" = {page} && '
                    '{ test "$state" = READY_LOCAL || test "$state" = DEGRADED_OFFLINE; }; then '
                    'cat /run/elo-client/health; found=1; break; fi; fi; sleep 1; done; '
                    'if test "$found" = 1; then true; else cat /run/elo-client/client.log; cat /run/elo-client/health; false; fi')
            try:
                sock = base / 'qmp.sock'
                network = ['-nic', 'none'] if not maintenance else [
                    '-netdev', f'user,id=maintenance,hostfwd=tcp:127.0.0.1:{maintenance.ssh_port}-:22',
                    '-device', 'virtio-net-device,netdev=maintenance', '-rtc', 'base=2000-01-01']
                proc = subprocess.Popen([os.environ.get('QEMU', 'qemu-system-aarch64'), '-machine', 'virt',
                    '-cpu', 'max', '-accel', 'tcg', '-m', '1024M', '-smp', '2', '-kernel', str(kernel),
                    '-append', 'root=/dev/vda rootwait console=ttyAMA0 consoleblank=0',
                    '-drive', f'file={image},if=none,format=raw,id=root,snapshot=on',
                    '-device', 'virtio-blk-device,drive=root', '-device', 'virtio-gpu-pci,xres=1024,yres=768',
                    *network, '-display', 'none', '-serial', 'stdio', '-no-reboot',
                    '-qmp', f'unix:{sock},server=on,wait=off'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)
                wait_for(rb'login:'); send('root'); wait_for(rb'# ')
                qmp = gui.Qmp(sock)
                command('boot-started-supervisor-without-client-command', 'test -s /run/elo-client/supervisor.pid && kill -0 "$(cat /run/elo-client/supervisor.pid)"')
                health(1)
                qmp.execute('screendump', {'filename': str(out / 'autostart-first.ppm')})
                health(2)
                qmp.execute('screendump', {'filename': str(out / 'autostart-image.ppm')})
                health(1)
                command('recover-after-kill', 'old=$(cat /run/elo-client/child.pid); kill -KILL "$old"; '
                    'found=0; for n in $(seq 1 20); do sleep 1; new=$(cat /run/elo-client/child.pid 2>/dev/null); '
                    'if test -n "$new" && test "$new" != "$old"; then found=1; break; fi; done; test "$found" = 1')
                health(2)
                if maintenance:
                    remote = maintenance.ssh('echo SSH_READY; date -u +%s; test -s /etc/dropbear/dropbear_ed25519_host_key')
                    assert remote.returncode == 0, remote.stdout + remote.stderr
                    assert 'SSH_READY' in remote.stdout
                    report['checks'].append('ssh-public-key-login')
                    wrong = base / 'wrong-ssh-key'
                    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(wrong)], check=True)
                    assert maintenance.ssh('true', key=wrong).returncode != 0, 'Unknown SSH key accepted'
                    report['checks'].append('unknown-ssh-key-rejected')
                    # Clock starts at RTC year 2000 + a stale local floor. NTP must repair it.
                    synchronized = False
                    for _ in range(20):
                        remote = maintenance.ssh('date -u +%s')
                        if remote.returncode == 0 and abs(int(remote.stdout.strip()) - time.time()) < 30:
                            synchronized = True; break
                        time.sleep(1)
                    assert synchronized and maintenance.ntp_requests > 0, 'NTP did not synchronize stale clock'
                    report['checks'].append('ntp-corrects-stale-clock')
                    diagnostic = maintenance.ssh('elo-diagnose')
                    assert diagnostic.returncode == 0 and 'HTTP: 200' in diagnostic.stdout, diagnostic.stdout + diagnostic.stderr
                    assert 't' * 43 not in diagnostic.stdout + diagnostic.stderr
                    report['checks'].append('remote-diagnostic-and-verified-https')
                    assert maintenance.downloads > 0
                    for _ in range(15):
                        if maintenance.report and maintenance.report.get('display'): break
                        time.sleep(1)
                    assert maintenance.report and maintenance.report.get('display'), 'Native terminal did not report to server'
                    report['checks'].append('native-presentation-report-after-clock-sync')
                    # Serial console remains available while server and SSH route is lost.
                    before_pid = maintenance.ssh('cat /run/elo-client/child.pid').stdout.strip()
                    command('lose-server-route', 'echo ELO_TEST_ROUTE_LOSS >> /run/elo-client/client.log; ip route add unreachable 10.0.2.2/32')
                    try:
                        command('observe-offline-retry',
                            'found=0; for n in $(seq 1 75); do '
                            "if sed -n '/ELO_TEST_ROUTE_LOSS/,$p' /run/elo-client/client.log | grep -q fetch_failed; "
                            'then found=1; break; fi; sleep 1; done; test "$found" = 1')
                    finally:
                        command('restore-server-route', 'ip route del unreachable 10.0.2.2/32')
                    downloads = maintenance.downloads
                    sequence = maintenance.report.get('sequence', 0)
                    deadline = time.monotonic() + 90
                    while time.monotonic() < deadline:
                        if maintenance.downloads > downloads and maintenance.report.get('sequence', 0) > sequence: break
                        time.sleep(1)
                    else: raise AssertionError('Client did not recover after server route returned')
                    assert maintenance.ssh('cat /run/elo-client/child.pid').stdout.strip() == before_pid
                    report['checks'].append('route-loss-and-recovery-without-client-restart')
                    stopped = maintenance.ssh('/etc/init.d/S50elo-client stop; echo MAINTENANCE_ALIVE')
                    assert stopped.returncode == 0 and 'MAINTENANCE_ALIVE' in stopped.stdout
                    assert maintenance.ssh('test ! -e /run/elo-client/child.pid; echo SSH_STILL_ALIVE').returncode == 0
                    report['checks'].append('ssh-survives-presentation-stop')
                command('stop-cleanly', '/etc/init.d/S50elo-client stop && test ! -e /run/elo-client/child.pid')
                send('poweroff'); proc.wait(timeout=30)
                assert proc.returncode == 0
                report['checks'].append('clean-shutdown')
                report['status'] = 'PASS'
            finally:
                if qmp: qmp.close()
                if proc and proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait()
                report['original_sha256_after'] = gui.digest(original)
                if report['original_sha256'] != report['original_sha256_after']: report['status'] = 'FAIL'
                if maintenance: maintenance.close()
                (out / ('maintenance-qemu.json' if maintenance_mode else 'autostart-qemu.json')).write_text(json.dumps(report, indent=2) + '\n')
    assert report['status'] == 'PASS'
    if maintenance_mode:
        print('PASS Pi maintenance: SSH key, NTP clock repair, verified HTTPS, remote diagnosis and native reports; isolated virtual NIC')
    else:
        print('PASS Pi rootfs: automatic boot, JPEG, loop and crash recovery, no NIC/mouse/keyboard; NOT physical Pi/Wi-Fi')


if __name__ == '__main__': main()
