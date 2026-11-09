#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Pi client rootfs on a generic ARM64 kernel; never a physical Pi/Wi-Fi test."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import select
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('gui_smoke', ROOT / 'tests/client/qemu-gui-smoke.py')
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)


def main():
    out = Path(os.environ.get('OUTPUT_DIR', ROOT / 'output/pi5-client')).resolve()
    kernel = Path(os.environ.get('QEMU_TEST_KERNEL', ROOT / 'output/toolbox/qemu-aarch64-gui/images/Image')).resolve()
    rootfs = out / 'images/rootfs.ext4'
    assert rootfs.is_file() and kernel.is_file(), 'Build rootfs and a generic QEMU ARM64 kernel first'
    report = {'status': 'FAIL', 'scope': 'Pi client rootfs with generic virt ARM64 kernel; no Pi firmware, VC4 or Wi-Fi validation',
              'rootfs_sha256_before': gui.digest(rootfs), 'kernel': str(kernel),
              'kernel_sha256': gui.digest(kernel), 'checks': []}
    proc = qmp = None
    deadline = time.monotonic() + 240
    buffer = b''
    with tempfile.TemporaryDirectory(prefix='elo-pi-rootfs-') as temp, (out / 'rootfs-qemu.log').open('wb') as log, (out / 'rootfs-qemu-stderr.log').open('wb') as errors:
        def wait_for(pattern):
            nonlocal buffer
            while time.monotonic() < deadline:
                match = re.search(pattern, buffer)
                if match:
                    output = buffer[:match.start()]
                    buffer = buffer[match.end():]
                    return match, output
                if select.select([proc.stdout], [], [], 0.2)[0]:
                    chunk = os.read(proc.stdout.fileno(), 65536)
                    if not chunk:
                        raise RuntimeError('QEMU closed console')
                    log.write(chunk)
                    log.flush()
                    buffer += chunk
                    if b'Kernel panic' in buffer or b'Oops:' in buffer:
                        raise RuntimeError('Kernel failure')
            raise TimeoutError(str(pattern))

        def send(command):
            proc.stdin.write(command.encode() + b'\n')
            proc.stdin.flush()

        def command(name, body):
            nonce = secrets.token_hex(8)
            send('{ ' + body + "; }; rc=$?; printf '\\n%s%s:%s\\n' ELO_ " + nonce + ' "$rc"')
            match, output = wait_for(rb'(?m)^ELO_' + nonce.encode() + rb':([0-9]+)\r?$')
            if match[1] != b'0':
                raise RuntimeError(name + ': ' + output.decode(errors='replace'))
            wait_for(rb'# ')
            report['checks'].append(name)
            return output.decode(errors='replace')

        def health(page):
            return command('rendered-page-' + str(page),
                'found=0; for n in $(seq 1 30); do '
                'if test -s /run/bench.health; then '
                'read -r magic token pid stamp sequence state page digest < /run/bench.health; '
                f'if test "$magic" = ELO_HEALTH_V1 && test "$sequence" -ge 2 && test "$page" = {page}; then '
                'cat /run/bench.health; found=1; break; fi; fi; sleep 1; done; test "$found" = 1')

        def frame(name):
            path = out / ('rootfs-' + name + '.ppm')
            qmp.execute('screendump', {'filename': str(path)})
            data = path.read_bytes()
            match = re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s', data)
            assert match and int(match[1]) >= 640 and int(match[2]) >= 480
            pixels = data[match.end():]
            assert len(set(pixels[n:n+3] for n in range(0, len(pixels), 48))) >= 8
            return hashlib.sha256(pixels).hexdigest()

        try:
            sock = Path(temp) / 'qmp.sock'
            proc = subprocess.Popen([os.environ.get('QEMU', 'qemu-system-aarch64'),
                '-machine', 'virt', '-cpu', 'cortex-a53', '-accel', 'tcg', '-m', '1024M', '-smp', '2',
                '-kernel', str(kernel), '-append', 'root=/dev/vda rootwait console=ttyAMA0',
                '-drive', f'file={rootfs},if=none,format=raw,id=root,snapshot=on',
                '-device', 'virtio-blk-device,drive=root', '-nic', 'none', '-display', 'none',
                '-device', 'virtio-gpu-pci,xres=1024,yres=768', '-device', 'virtio-keyboard-pci',
                '-device', 'virtio-mouse-pci', '-serial', 'stdio', '-no-reboot',
                '-qmp', f'unix:{sock},server=on,wait=off'], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=errors)
            wait_for(rb'login:')
            send('root')
            wait_for(rb'# ')
            qmp = gui.Qmp(sock)
            command('framebuffer-and-tools', 'test -c /dev/fb0 && command -v elo-client-start && command -v wpa_passphrase && command -v iw')
            command('wifi-config-absent-does-not-block-login', 'test ! -s /etc/elo-wifi.conf && /etc/init.d/S41elo-wifi start')
            command('manual-client-start', 'elo-client-start --health-file /run/bench.health --health-token pi5-rootfs >/run/bench.log 2>&1 & echo $! >/run/bench.pid')
            report['initial_health'] = health(1)
            report['ready_frame'] = frame('ready')
            qmp.key('right')
            health(2)
            report['next_frame'] = frame('next')
            assert report['ready_frame'] != report['next_frame'], 'Keyboard navigation did not change screen'
            qmp.key('esc')
            command('escape-exits-client', 'stopped=0; for n in $(seq 1 15); do if ! kill -0 "$(cat /run/bench.pid)" 2>/dev/null; then stopped=1; break; fi; sleep 1; done; test "$stopped" = 1')
            send('poweroff')
            proc.wait(timeout=30)
            assert proc.returncode == 0
            report['checks'].append('clean-shutdown')
            report['status'] = 'PASS'
        finally:
            if qmp:
                qmp.close()
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            report['rootfs_sha256_after'] = gui.digest(rootfs)
            if report['rootfs_sha256_before'] != report['rootfs_sha256_after']:
                report['status'] = 'FAIL'
            (out / 'rootfs-qemu.json').write_text(json.dumps(report, indent=2) + '\n')
    assert report['status'] == 'PASS'
    print('PASS Pi client rootfs: software framebuffer, keyboard, Escape, shutdown; NOT physical Pi/Wi-Fi')


if __name__ == '__main__':
    main()
