#!/usr/bin/env python3
"""Exercise two real boots; record logs, hashes and property checks on the host."""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import select
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
PROFILE = os.environ.get("PROFILE", "qemu-x86_64")
PROFILES = {"qemu-x86_64": ("x86_64", "bzImage", "ttyS0"),
            "qemu-aarch64": ("aarch64", "Image", "ttyAMA0")}
LOGIN = rb"elo-os login: "
PANIC = rb"Kernel panic|Oops:|BUG: unable to handle"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def boot(session, out, arch, console, mode):
    log_path = out / f"qemu-smoke-{mode}-{session}.log"
    result = {"session": session, "log": str(log_path), "status": "FAIL", "checks": []}
    deadline = time.monotonic() + float(os.environ.get("QEMU_BOOT_TIMEOUT", "180"))
    idle_seconds = float(os.environ.get("QEMU_IDLE_SECONDS", "3"))
    if idle_seconds < 1:
        raise ValueError("QEMU_IDLE_SECONDS deve ser >= 1")
    with log_path.open("wb") as log:
        proc = subprocess.Popen([str(ROOT / "scripts/run-qemu.sh")], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        result["host_qemu_pid"] = proc.pid
        buffer = b""
        transcript = b""
        allow_login = True

        def read_more(timeout):
            nonlocal buffer, transcript
            if select.select([proc.stdout], [], [], timeout)[0]:
                data = os.read(proc.stdout.fileno(), 65536)
                if not data:
                    raise RuntimeError("QEMU encerrou antes do critério esperado")
                log.write(data)
                log.flush()
                buffer += data
                transcript += data
            if re.search(PANIC, buffer):
                raise RuntimeError("Panic/Oops observado no console")
            if not allow_login and re.search(LOGIN, buffer):
                raise RuntimeError("Login reapresentado sem exit: possível respawn de getty")

        def wait_for(pattern):
            nonlocal buffer
            while time.monotonic() < deadline:
                match = re.search(pattern, buffer)
                if match:
                    prefix = buffer[:match.start()]
                    buffer = buffer[match.end():]
                    return match, prefix
                read_more(min(1, max(0, deadline - time.monotonic())))
            raise TimeoutError(f"Console não atingiu {pattern!r}")

        def observe_idle():
            until = time.monotonic() + idle_seconds
            while time.monotonic() < until:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Timeout durante estabilidade do console")
                read_more(min(0.25, until - time.monotonic()))
            result["checks"].append("console-idle-stable")

        def send(command):
            proc.stdin.write(command.encode() + b"\n")
            proc.stdin.flush()

        def command(name, body):
            # The full nonce marker is never present in the submitted command.
            # A serial echo cannot satisfy this assertion, even if echo is enabled.
            nonce = secrets.token_hex(8)
            send("{ " + body + "; }; rc=$?; printf '\\n%s%s:%s\\n' ELO_ " + nonce + ' "$rc"')
            match, output = wait_for(rb"(?m)^ELO_" + nonce.encode() + rb":([0-9]+)\r?$")
            if match[1] != b"0":
                raise RuntimeError(f"Comando {name} falhou: {output.decode(errors='replace')}")
            wait_for(rb"# ")
            return output.decode(errors="replace").replace("\r", "")

        try:
            wait_for(LOGIN)
            allow_login = False
            observe_idle()
            send("root")
            wait_for(rb"# ")
            send("stty -echo")
            wait_for(rb"# ")
            observe_idle()
            output = command("architecture", "uname -m")
            if not re.search(rf"(?m)^{arch}$", output):
                raise RuntimeError(f"Arquitetura incorreta: {output!r}")
            result["checks"].append("architecture")
            output = command("identity", "cat /etc/elo-os-release")
            for line in ('NAME="ELO/OS"', f'VERSION="{(ROOT / "VERSION").read_text().strip()}"',
                         f'PLATFORM="{PROFILE}"'):
                if line not in output.splitlines():
                    raise RuntimeError(f"Identidade ausente: {line}")
            result["checks"].append("identity")
            output = command("pid1", "cat /proc/1/comm; readlink /proc/1/exe")
            if not re.search(r"(?m)^init$", output) or not re.search(r"(?m)^/.*busybox$", output):
                raise RuntimeError(f"PID 1 não é BusyBox init: {output!r}")
            result["checks"].append("busybox-pid1")
            output = command("cmdline", "cat /proc/cmdline")
            if "root=/dev/vda" not in output.split() or f"console={console}" not in output.split():
                raise RuntimeError(f"Cmdline incorreta: {output!r}")
            result["checks"].append("cmdline-console")
            output = command("mounts", "cat /proc/mounts; test -b /dev/vda")
            root = re.search(r"(?m)^\S+ / ext4 (\S+) ", output)
            if not root or "rw" not in root[1].split(","):
                raise RuntimeError("Raiz ext4 RW e disco virtio não demonstrados")
            for mountpoint in ("/run", "/tmp"):
                if not re.search(rf"(?m)^\S+ {mountpoint} tmpfs ", output):
                    raise RuntimeError(f"tmpfs não observado em {mountpoint}")
            result["checks"].append("ext4-rw-virtio-tmpfs")
            output = command("network", "ip -4 addr show; ip route")
            addresses = re.findall(r"inet ([0-9.]+/[0-9]+)", output)
            addresses = [a for a in addresses if not ipaddress.ip_interface(a).ip.is_loopback]
            route = re.search(r"(?m)^default via ([0-9.]+) dev (\S+)", output)
            leases = re.findall(rb"udhcpc: lease of ([0-9.]+) obtained", transcript)
            if not addresses or not route or not leases:
                raise RuntimeError("IPv4, lease DHCP e rota padrão não demonstrados")
            if leases[-1].decode() not in [a.split("/")[0] for a in addresses]:
                raise RuntimeError("Endereço observado não corresponde à concessão DHCP")
            ipaddress.IPv4Address(route[1])
            result["network"] = {"addresses": addresses, "gateway": route[1], "interface": route[2]}
            result["checks"].append("dhcp-ipv4-default-route")
            result["memory_kib"] = command("memory", "free -k")
            command("snapshot", "test ! -e /root/elo-qemu-snapshot-probe && "
                    "echo probe > /root/elo-qemu-snapshot-probe && sync && "
                    "test -s /root/elo-qemu-snapshot-probe")
            result["checks"].append("snapshot-probe")
            send("poweroff")
            wait_for(rb"reboot: Power down")
            proc.wait(timeout=15)
            result["qemu_exit_code"] = proc.returncode
            if proc.returncode != 0:
                raise RuntimeError(f"QEMU encerrou com código {proc.returncode}")
            result["checks"].append("poweroff")
            result["status"] = "PASS"
        except (Exception, KeyboardInterrupt) as err:
            result["error"] = str(err)
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
    print(f'{result["status"]}: {PROFILE}, boot {session} ({log_path})', flush=True)
    return result


def main():
    if PROFILE not in PROFILES:
        raise SystemExit("PROFILE deve ser qemu-x86_64 ou qemu-aarch64")
    arch, kernel, console = PROFILES[PROFILE]
    out = Path(os.environ.get("OUTPUT_DIR", ROOT / "output" / PROFILE)).resolve()
    images = [out / "images" / name for name in (kernel, "rootfs.ext4")]
    if not all(path.is_file() for path in images):
        raise SystemExit(f"Compile primeiro: PROFILE={PROFILE} ./scripts/build.sh")
    mode = os.environ.get("QEMU_ACCEL", "auto")
    if mode not in ("auto", "kvm", "tcg"):
        raise SystemExit("QEMU_ACCEL deve ser kvm ou tcg")
    report_path = out / f"qemu-smoke-{mode}.json"
    report = {"profile": PROFILE, "time_utc": datetime.now(timezone.utc).isoformat(),
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_dirty": bool(subprocess.run(["git", "diff", "--quiet"], cwd=ROOT).returncode),
              "defconfig_sha256": digest(ROOT / "configs" / f"elo_qemu_{arch}_defconfig"),
              "hashes_before": {p.name: digest(p) for p in images}, "sessions": [], "status": "FAIL"}
    try:
        for session in (1, 2):
            result = boot(session, out, arch, console, mode)
            report["sessions"].append(result)
            if result["status"] != "PASS":
                raise RuntimeError(result.get("error", "Boot não aprovado"))
        report["status"] = "PASS"
    except (Exception, KeyboardInterrupt) as err:
        report["error"] = str(err)
    finally:
        report["hashes_after"] = {p.name: digest(p) for p in images}
        if report["hashes_before"] != report["hashes_after"]:
            report["status"] = "FAIL"
            report["error"] = "Imagem base mudou durante o ensaio"
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f'{report["status"]}: snapshot, hashes e dois boots; relatório: {report_path}', flush=True)
    if report["status"] != "PASS":
        print(report.get("error", "Falha no ensaio"), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
