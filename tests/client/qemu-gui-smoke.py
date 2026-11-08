#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Boot the isolated GUI image with no NIC; exercise real rendering and input via QMP."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import select
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class Qmp:
    def __init__(self, path):
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.settimeout(10)
        self.socket.connect(str(path))
        self.file = self.socket.makefile('rwb')
        if 'QMP' not in json.loads(self.file.readline()):
            raise RuntimeError('QMP greeting missing')
        self.execute('qmp_capabilities')

    def execute(self, name, arguments=None):
        nonce = secrets.token_hex(8)
        request = {'execute': name, 'id': nonce}
        if arguments is not None:
            request['arguments'] = arguments
        self.file.write(json.dumps(request).encode() + b'\n')
        self.file.flush()
        while True:
            line = self.file.readline()
            if not line:
                raise RuntimeError('QMP disconnected')
            reply = json.loads(line)
            if reply.get('id') == nonce:
                if 'error' in reply:
                    raise RuntimeError(str(reply['error']))
                return reply.get('return')

    def key(self, key):
        self.execute('send-key', {'keys': [{'type': 'qcode', 'data': key}], 'hold-time': 80})

    def close(self):
        self.file.close()
        self.socket.close()


def main():
    profile = os.environ.get('PROFILE', 'qemu-x86_64-gui')
    if profile not in ('qemu-x86_64-gui', 'qemu-aarch64-gui'):
        raise SystemExit('PROFILE deve ser qemu-x86_64-gui ou qemu-aarch64-gui')
    arch = 'aarch64' if 'aarch64' in profile else 'x86_64'
    out = Path(os.environ.get('OUTPUT_DIR', ROOT / 'output' / profile)).resolve()
    kernel = 'Image' if arch == 'aarch64' else 'bzImage'
    images = [out / 'images' / name for name in (kernel, 'rootfs.ext4')]
    emulator = os.environ.get('QEMU', f'qemu-system-{arch}')
    report = {'profile': profile, 'time_utc': datetime.now(timezone.utc).isoformat(),
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'source_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)),
              'qemu_binary': emulator,
              'qemu_module_dir': os.environ.get('QEMU_MODULE_DIR', 'default'),
              'config_sha256': digest(out / '.config'),
              'hashes_before': {p.name: digest(p) for p in images},
              'network': 'no virtual NIC', 'status': 'FAIL', 'checks': []}
    started = time.monotonic()
    deadline = started + float(os.environ.get('QEMU_BOOT_TIMEOUT', '240'))
    proc = None
    qmp = None
    with tempfile.TemporaryDirectory(prefix='elo-gui-') as temp, (out / 'gui-smoke.log').open('wb') as log:
        path = Path(temp) / 'qmp.sock'
        env = {**os.environ, 'PROFILE': profile, 'QEMU_NETWORK': 'off', 'QEMU_DISPLAY': 'none'}
        buffer = b''

        def wait_for(pattern):
            nonlocal buffer
            while time.monotonic() < deadline:
                match = re.search(pattern, buffer)
                if match:
                    prefix = buffer[:match.start()]
                    buffer = buffer[match.end():]
                    return match, prefix
                if select.select([proc.stdout], [], [], 0.25)[0]:
                    data = os.read(proc.stdout.fileno(), 65536)
                    if not data:
                        raise RuntimeError('QEMU encerrou antes do critério')
                    log.write(data)
                    log.flush()
                    buffer += data
                    if re.search(rb'Kernel panic|Oops:', buffer):
                        raise RuntimeError('Kernel panic/Oops')
            raise TimeoutError(f'Console não atingiu {pattern!r}')

        def send(command):
            proc.stdin.write(command.encode() + b'\n')
            proc.stdin.flush()

        def command(name, body):
            nonce = secrets.token_hex(8)
            send('{ ' + body + "; }; rc=$?; printf '\\n%s%s:%s\\n' ELO_ " + nonce + ' "$rc"')
            match, output = wait_for(rb'(?m)^ELO_' + nonce.encode() + rb':([0-9]+)\r?$')
            if match[1] != b'0':
                raise RuntimeError(f'{name}: {output.decode(errors="replace")}')
            wait_for(rb'# ')
            report['checks'].append(name)
            return output.decode(errors='replace').replace('\r', '')

        def frame(name):
            frame_path = out / f'gui-{name}.ppm'
            qmp.execute('screendump', {'filename': str(frame_path)})
            data = frame_path.read_bytes()
            match = re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s', data)
            if not match:
                raise RuntimeError('QMP screendump não produziu PPM RGB')
            pixels = data[match.end():]
            width, height = int(match[1]), int(match[2])
            if len(pixels) != width * height * 3 or width < 640 or height < 480:
                raise RuntimeError('Framebuffer com dimensões inválidas')
            samples = [pixels[i:i+3] for i in range(0, len(pixels), 3 * 16)]
            if len(set(samples)) < 8 or samples.count(b'\x10\x1d\x23') < len(samples) // 4:
                raise RuntimeError('Framebuffer sem evidência de apresentação renderizada')
            return hashlib.sha256(pixels).hexdigest()

        try:
            report['qemu_version'] = subprocess.check_output([emulator, '--version'], text=True).splitlines()[0]
            proc = subprocess.Popen([str(ROOT / 'scripts/run-qemu.sh'), '-qmp',
                                     f'unix:{path},server=on,wait=off'], env=env,
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            report['host_qemu_pid'] = proc.pid
            wait_for(rb'elo-os login: ')
            send('root')
            wait_for(rb'# ')
            send('stty -echo')
            wait_for(rb'# ')
            result = command('architecture-identity', 'uname -m; uname -r; cat /etc/elo-os-release')
            if not re.search(rf'(?m)^{arch}$', result) or f'PLATFORM="{profile}"' not in result:
                raise RuntimeError('Arquitetura/identidade incorretas')
            report['guest_identity'] = result
            result = command('init-root', 'cat /proc/1/comm; readlink /proc/1/exe; '
                             'cat /proc/mounts; test -b /dev/vda')
            if (not re.search(r'(?m)^init$', result) or not re.search(r'(?m)^/.*busybox$', result)
                    or not re.search(r'(?m)^\S+ / ext4 ', result)):
                raise RuntimeError('BusyBox init e raiz ext4 não demonstrados')
            report['guest_init_mounts'] = result
            command('offline-no-nic', 'test "$(ls /sys/class/net)" = lo && test -z "$(ip route)"')
            command('client-running', 'cat /run/elo-client.log; '
                    'test -s /run/elo-client.pid && kill -0 "$(cat /run/elo-client.pid)" && '
                    'test "$(readlink /proc/$(cat /run/elo-client.pid)/exe)" = /usr/bin/elo-client')
            result = command('local-readiness', 'for n in $(seq 1 60); do '
                             'grep -q "state=READY_LOCAL" /run/elo-client.log && break; sleep 1; done; '
                             'cat /run/elo-client.log; /usr/bin/elo-client-core; '
                             'grep -q "state=READY_LOCAL" /run/elo-client.log')
            if 'state=READY_LOCAL' not in result or 'page=3/3' not in result:
                raise RuntimeError('Cliente local não demonstrado')
            if re.search(r'failed to load component|ReferenceError|TypeError|Cannot assign', result):
                raise RuntimeError('Erro QML observado')
            report['memory_kib'] = command('memory', 'free -k')
            report['client_memory'] = command('client-memory',
                'sed -n "/^VmRSS:/p; /^VmSize:/p; /^Threads:/p" /proc/$(cat /run/elo-client.pid)/status')
            report['qt_runtime_libraries'] = command('qt-runtime-libraries',
                "awk '/libQt6/ {print $NF}' /proc/$(cat /run/elo-client.pid)/maps | sort -u")
            if 'libQt6Core.so' not in report['qt_runtime_libraries']:
                raise RuntimeError('Biblioteca Qt Core carregada não demonstrada')
            qmp = Qmp(path)
            time.sleep(2)
            first = frame('ready')
            qmp.key('right')
            time.sleep(1)
            second = frame('next')
            if first == second:
                raise RuntimeError('Teclado não alterou a apresentação')
            qmp.key('home')
            time.sleep(1)
            reset = frame('reset')
            if first != reset:
                raise RuntimeError('Home não restaurou a apresentação inicial')
            report['frames_sha256'] = {'ready': first, 'next': second, 'reset': reset}
            report['checks'] += ['rendered-framebuffer', 'keyboard-next', 'keyboard-reset']
            send('poweroff')
            wait_for(rb'reboot: Power down')
            proc.wait(timeout=15)
            if proc.returncode != 0:
                raise RuntimeError(f'QEMU exit={proc.returncode}')
            report['checks'].append('poweroff')
            report['status'] = 'PASS'
        except (Exception, KeyboardInterrupt) as error:
            report['error'] = str(error)
        finally:
            if qmp:
                qmp.close()
            if proc:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                proc.stdin.close()
                proc.stdout.close()
            report['hashes_after'] = {p.name: digest(p) for p in images}
            log.flush()
            match = re.search(rb'ACCEL=(\w+)', (out / 'gui-smoke.log').read_bytes())
            report['qemu_acceleration'] = match[1].decode() if match else 'NOT_RECORDED'
            report['duration_seconds'] = round(time.monotonic() - started, 3)
            if report['hashes_before'] != report['hashes_after']:
                report['status'] = 'FAIL'
                report['error'] = 'Imagem base alterada'
            (out / 'gui-smoke.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'{report["status"]}: {profile}; {out / "gui-smoke.json"}')
    if report['status'] != 'PASS':
        print(report.get('error'), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
