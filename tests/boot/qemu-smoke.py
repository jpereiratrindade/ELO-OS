#!/usr/bin/env python3
"""Boot the virtual image twice; check console, DHCP and snapshot isolation."""
import os
from pathlib import Path
import re
import select
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get("OUTPUT_DIR", ROOT / "output/qemu-x86_64"))


def boot(session):
    log_path = OUT / f"qemu-smoke-{session}.log"
    deadline = time.monotonic() + 120
    with log_path.open("wb") as log:
        proc = subprocess.Popen(
            [str(ROOT / "scripts/run-qemu.sh")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        buffer = b""

        def wait_for(pattern):
            nonlocal buffer
            while time.monotonic() < deadline:
                match = re.search(pattern, buffer)
                if match:
                    buffer = buffer[match.end():]
                    return
                if select.select([proc.stdout], [], [], 1)[0]:
                    data = os.read(proc.stdout.fileno(), 65536)
                    if not data:
                        break
                    log.write(data)
                    log.flush()
                    buffer += data
            raise RuntimeError(f"Console não atingiu {pattern!r}; veja {log_path}")

        def send(command):
            proc.stdin.write(command.encode() + b"\n")
            proc.stdin.flush()

        try:
            wait_for(rb"elo-os login: ")
            send("root")
            wait_for(rb"# ")
            # Assertions should only match guest output, not command echo.
            send("stty -echo")
            wait_for(rb"# ")
            send("uname -m; cat /etc/elo-os-release; ip -4 addr show eth0; ip route")
            wait_for(rb"(?:^|\r?\n)x86_64\r?\n")
            wait_for(rb'PLATFORM="qemu-x86_64"')
            wait_for(rb"inet 10\.0\.2\.15/")
            wait_for(rb"default via 10\.0\.2\.2 dev eth0")
            wait_for(rb"# ")
            send("test ! -e /root/elo-qemu-snapshot-probe && "
                 "touch /root/elo-qemu-snapshot-probe && "
                 "sync && echo ELO_SNAPSHOT_OK")
            wait_for(rb"(?:^|\r?\n)ELO_SNAPSHOT_OK\r?\n")
            send("poweroff")
            wait_for(rb"reboot: Power down")
            proc.wait(timeout=15)
            if proc.returncode != 0:
                raise RuntimeError(f"QEMU encerrou com código {proc.returncode}: {log_path}")
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            proc.stdin.close()
            proc.stdout.close()
    print(f"PASS: boot {session}, login, identidade, DHCP, snapshot e poweroff ({log_path})")


if __name__ == "__main__":
    if not (OUT / "images/rootfs.ext4").is_file():
        raise SystemExit("Compile primeiro: PROFILE=qemu-x86_64 ./scripts/build.sh")
    boot(1)
    boot(2)
    print("PASS: escrita da primeira sessão não persistiu na segunda")
