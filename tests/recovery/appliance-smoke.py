#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Exercise persistent data on disposable regular-file QEMU disks only."""
import hashlib
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


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class Session:
    def __init__(self, env, log_path):
        self.log = log_path.open('wb')
        self.diagnostics = log_path.with_suffix('.qemu.log').open('wb')
        self.buffer = b''
        self.proc = subprocess.Popen([str(ROOT / 'scripts/run-qemu.sh')], env=env,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.diagnostics)
        try:
            boot = self.wait(rb'elo-os login: ')[1]
            marker = b'elo-boot presentation-ready-before-network'
            if marker not in boot or boot.index(marker) > boot.index(b'Starting network:'):
                raise RuntimeError('Local presentation before network not demonstrated')
            self.send('root')
            self.wait(rb'# ')
            self.send('stty -echo')
            self.wait(rb'# ')
        except BaseException:
            self.close()
            raise

    def wait(self, pattern, timeout=90):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            match = re.search(pattern, self.buffer)
            if match:
                output = self.buffer[:match.start()]
                self.buffer = self.buffer[match.end():]
                return match, output
            if select.select([self.proc.stdout], [], [], 0.2)[0]:
                data = os.read(self.proc.stdout.fileno(), 65536)
                if not data:
                    raise RuntimeError('QEMU exited before console criterion')
                self.log.write(data)
                self.log.flush()
                self.buffer += data
                if re.search(rb'Kernel panic|Oops:', self.buffer):
                    raise RuntimeError('Kernel panic/Oops')
        raise TimeoutError(f'Console did not reach {pattern!r}')

    def send(self, text):
        self.proc.stdin.write(text.encode() + b'\n')
        self.proc.stdin.flush()

    def command(self, body):
        nonce = secrets.token_hex(8)
        self.send('{ ' + body + "; }; rc=$?; printf '\\nELO_DATA_" + nonce + ":%s\\n' \"$rc\"")
        match, output = self.wait(rb'(?m)^ELO_DATA_' + nonce.encode() + rb':([0-9]+)\r?$')
        self.wait(rb'# ')
        if match[1] != b'0':
            raise RuntimeError(f'Guest command failed (exit={match[1].decode()}): {body}\n'
                               + output.decode(errors='replace'))
        return output.decode(errors='replace').replace('\r', '')

    def poweroff(self):
        self.send('poweroff')
        self.wait(rb'reboot: Power down')
        if self.proc.wait(timeout=15) != 0:
            raise RuntimeError('QEMU failed to power off cleanly')

    def kill(self):
        self.proc.kill()
        self.proc.wait(timeout=10)

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.proc.stdin.close()
        self.proc.stdout.close()
        self.log.close()
        self.diagnostics.close()


def main():
    profile = os.environ.get('PROFILE', 'qemu-x86_64-appliance')
    if profile not in ('qemu-x86_64-appliance', 'qemu-aarch64-appliance'):
        raise SystemExit('Use PROFILE=qemu-{x86_64,aarch64}-appliance')
    out = Path(os.environ.get('OUTPUT_DIR', ROOT / 'output' / profile)).resolve()
    kernel = 'Image' if 'aarch64' in profile else 'bzImage'
    bases = [out / 'images' / name for name in (kernel, 'rootfs.ext4')]
    report = {'profile': profile, 'source_commit': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT)),
        'status': 'FAIL', 'checks': [], 'hashes_before': {p.name: digest(p) for p in bases},
        'fault_model': 'SIGKILL of QEMU after fsync; not physical power loss'}
    started = time.monotonic()
    session = None
    try:
        with tempfile.TemporaryDirectory(prefix='data-smoke-', dir=out) as temp:
            image = Path(temp) / 'data.ext4'
            env = {**os.environ, 'PROFILE': profile, 'OUTPUT_DIR': str(out),
                   'QEMU_DATA_IMAGE': str(image), 'QEMU_DATA': 'on',
                   'QEMU_NETWORK': 'off', 'QEMU_DISPLAY': 'none', 'DATA_SIZE_MIB': '32'}
            created = subprocess.run([str(ROOT / 'scripts/create-data-image.sh')],
                                     env=env, capture_output=True, text=True)
            if created.returncode:
                raise RuntimeError(created.stderr)
            original = secrets.token_hex(16)
            updated = secrets.token_hex(16)

            def boot(name):
                return Session(env, out / f'data-smoke-{name}.log')

            def ready(current):
                current.command('grep -qx "ELO_STORAGE_V1 READY MOUNTED" /run/elo-storage/status && '
                                'test "$(cat /data/.elo-layout)" = ELO_DATA_V1 && '
                                'grep -q " / ext4 ro," /proc/mounts && '
                                'test ! -e /etc/.elo-data-probe && ! touch /etc/.elo-data-probe')

            session = boot('fresh')
            ready(session)
            session.command(f"printf '%s\\n' {original} > /data/state/sentinel && "
                            'fsync /data/state/sentinel && fsync /data/state')
            report['checks'].append('fresh-data-initialized-root-read-only')
            # Persist the on-disk intermediate state of interrupted first setup.
            session.command("printf incomplete > /data/.elo-layout.stale && "
                            'rm /data/.elo-layout && fsync /data/.elo-layout.stale && fsync /data')
            session.kill()
            session.close()
            session = boot('after-kill')
            ready(session)
            session.command(f'test "$(cat /data/state/sentinel)" = {original}')
            report['checks'].append('fsynced-state-survives-qemu-sigkill')
            report['checks'].append('partial-layout-setup-recovers-without-dropping-state')
            session.command(f"printf '%s\\n' {updated} > /data/state/.staged && "
                            'fsync /data/state/.staged && fsync /data/state')
            session.kill()
            session.close()
            session = boot('staged')
            ready(session)
            session.command(f'test "$(cat /data/state/sentinel)" = {original} && '
                            f'test "$(cat /data/state/.staged)" = {updated}')
            report['checks'].append('uncommitted-staging-does-not-replace-state')
            session.command('if dd if=/dev/zero of=/data/state/fill bs=1048576 count=64; '
                            'then false; else true; fi')
            # A failed 1 MiB dd write can leave smaller free extents. Require
            # a 2 MiB candidate to fail, rather than assuming zero free bytes.
            session.command('if (dd if=/dev/zero of=/data/state/.candidate bs=1048576 count=2 && '
                            'fsync /data/state/.candidate); '
                            f'then false; else test "$(cat /data/state/sentinel)" = {original}; fi')
            report['checks'].append('enospc-candidate-fails-previous-state-preserved')
            session.command('rm -f /data/state/fill /data/state/.candidate && '
                            'mv /data/state/.staged /data/state/sentinel && '
                            'fsync /data/state/sentinel && fsync /data/state')
            session.poweroff()
            session.close()
            session = boot('committed')
            ready(session)
            session.command(f'test "$(cat /data/state/sentinel)" = {updated}')
            report['checks'].append('committed-state-survives-clean-reboot')
            session.command("printf 'FUTURE_LAYOUT\\n' > /data/.elo-layout && fsync /data/.elo-layout && fsync /data")
            session.poweroff()
            session.close()
            session = boot('unknown-layout')
            session.command('grep -qx "ELO_STORAGE_V1 UNAVAILABLE LAYOUT_VERSION" /run/elo-storage/status && '
                            '! mountpoint -q /data && ! touch /data/.elo-data-probe && '
                            'mkdir -p /run/data-inspect && '
                            'mount -t ext4 -o ro,noload /dev/vdb /run/data-inspect && '
                            'test "$(cat /run/data-inspect/.elo-layout)" = FUTURE_LAYOUT && '
                            f'test "$(cat /run/data-inspect/state/sentinel)" = {updated} && '
                            'umount /run/data-inspect')
            report['checks'].append('unknown-layout-refused-without-reinitialization')
            session.command('mount -t ext4 /dev/vdb /run/data-inspect && '
                            "printf 'ELO_DATA_V1\\n' > /run/data-inspect/.elo-layout && "
                            'mv /run/data-inspect/state /run/data-inspect/state.saved && '
                            'ln -s /etc /run/data-inspect/state && '
                            'fsync /run/data-inspect/.elo-layout && fsync /run/data-inspect && '
                            'umount /run/data-inspect')
            session.poweroff()
            session.close()
            session = boot('invalid-structure')
            session.command('grep -qx "ELO_STORAGE_V1 UNAVAILABLE INVALID_LAYOUT" /run/elo-storage/status && '
                            '! mountpoint -q /data && ! touch /data/.elo-data-probe && '
                            'mkdir -p /run/data-inspect && '
                            'mount -t ext4 -o ro,noload /dev/vdb /run/data-inspect && '
                            'test -L /run/data-inspect/state && '
                            f'test "$(cat /run/data-inspect/state.saved/sentinel)" = {updated} && '
                            'umount /run/data-inspect')
            report['checks'].append('symlink-in-layout-refused-state-preserved')
            session.poweroff()
            session.close()

            invalid = Path(temp) / 'unformatted.ext4'
            with invalid.open('wb') as stream:
                stream.truncate(32 * 1024 * 1024)
            invalid_before = digest(invalid)
            env['QEMU_DATA_IMAGE'] = str(invalid)
            session = boot('unformatted')
            session.command('grep -q "^ELO_STORAGE_V1 UNAVAILABLE " /run/elo-storage/status && '
                            '! mountpoint -q /data && ! touch /data/.elo-data-probe')
            session.poweroff()
            session.close()
            if digest(invalid) != invalid_before:
                raise RuntimeError('Invalid data disk was modified or formatted')
            report['checks'].append('unformatted-disk-refused-byte-for-byte-preserved')
            # Format only this owned disposable file to test a foreign volume.
            subprocess.run([str(out / 'host/sbin/mkfs.ext4'), '-q', '-L', 'OTHER_DATA',
                            '-m', '0', str(invalid)], check=True, capture_output=True)
            foreign_before = digest(invalid)
            session = boot('foreign-label')
            session.command('grep -qx "ELO_STORAGE_V1 UNAVAILABLE WRONG_LABEL" /run/elo-storage/status && '
                            '! mountpoint -q /data && ! touch /data/.elo-data-probe')
            session.poweroff()
            session.close()
            if digest(invalid) != foreign_before:
                raise RuntimeError('Foreign filesystem was modified')
            report['checks'].append('foreign-volume-refused-byte-for-byte-preserved')
            report['status'] = 'PASS'
    except (Exception, KeyboardInterrupt) as error:
        report['error'] = str(error)
    finally:
        if session:
            session.close()
        report['hashes_after'] = {p.name: digest(p) for p in bases}
        if report['hashes_before'] != report['hashes_after']:
            report['status'] = 'FAIL'
            report['error'] = 'Base system image changed'
        report['duration_seconds'] = round(time.monotonic() - started, 3)
        (out / 'data-smoke.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'{report["status"]}: {profile}; {out / "data-smoke.json"}')
    if report['status'] != 'PASS':
        print(report.get('error'))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
