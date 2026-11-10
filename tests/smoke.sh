#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
for file in README.md LICENSE VERSION external.desc external.mk Config.in \
  configs/elo_pi5_defconfig configs/elo_qemu_x86_64_defconfig configs/elo_qemu_aarch64_defconfig \
  board/elo/common/rootfs-overlay/usr/share/elo-os/README \
  board/elo/pi5/rootfs-overlay/etc/elo-os-release \
  board/elo/qemu-x86_64/rootfs-overlay/etc/elo-os-release \
  board/elo/qemu-aarch64/rootfs-overlay/etc/elo-os-release \
  docs/ELO-OS-BASES-001_v0.1.0.md docs/ELO-OS-IMPL-001_v0.1.1.md docs/tests/acceptance.md \
  docs/ELO-OS-IMPL-002_v0.1.0.md docs/adr/ADR-009-local-client.md tests/client/README.md \
  package/elo-client/src/COPYING board/elo/common/rootfs-overlay/usr/share/licenses/elo-os/COPYING \
  scripts/profiles.sh scripts/build.sh scripts/run-qemu.sh scripts/doctor.sh scripts/inspect-image.sh scripts/menuconfig.sh \
  scripts/pi5-preflight.py tests/boot/pi5-preflight-test.py tests/boot/pi5-evidence-template.md \
  scripts/run-client.sh configs/elo_qemu_x86_64_gui_defconfig configs/elo_qemu_aarch64_gui_defconfig \
  package/elo-client/src/core/client.hpp package/elo-client/src/core/client.cpp \
  tests/config-smoke.py tests/boot/qemu-smoke.py package/elo-client/Config.in package/elo-client/elo-client.mk \
  scripts/elo_content.py package/elo-client/src/core/ports.hpp package/elo-client/src/core/events.hpp \
  package/elo-client/src/QtAdapters.cpp tests/client/local-content-test.py tests/client/supervisor-test.py \
  docs/tests/desktop-validation.md docs/client/local-contracts.md \
  board/elo/qemu-gui/rootfs-overlay/usr/bin/elo-client-supervisor \
  configs/elo_qemu_x86_64_appliance_defconfig configs/elo_qemu_aarch64_appliance_defconfig \
  board/elo/appliance/post-build.sh board/elo/appliance/busybox.fragment \
  board/elo/appliance/rootfs-overlay/etc/init.d/S35elo-data scripts/create-data-image.sh \
  tests/recovery/data-image-test.py tests/recovery/appliance-smoke.py \
  scripts/image-build-info.py docs/ELO-OS-IMPL-003_v0.1.0.md; do
  test -s "$ROOT/$file" || { echo "ERRO: faltando $file" >&2; exit 1; }
done
for file in "$ROOT"/board/elo/pi5-client/rootfs-overlay/usr/bin/* "$ROOT"/board/elo/pi5-client/rootfs-overlay/etc/init.d/*; do
  sh -n "$file"
done
for file in "$ROOT"/scripts/*.sh "$ROOT"/board/elo/pi5/*.sh; do
  bash -n "$file"
done
sh -n "$ROOT/package/elo-client/src/terminal.sh"
sh -n "$ROOT/board/elo/qemu-gui/rootfs-overlay/etc/init.d/S50elo-client"
sh -n "$ROOT/board/elo/qemu-gui/rootfs-overlay/usr/bin/elo-client-supervisor"
bash -n "$ROOT/board/elo/appliance/post-build.sh"
bash -n "$ROOT/board/elo/pi5-client/post-build.sh"
for file in "$ROOT"/board/elo/appliance/rootfs-overlay/etc/init.d/*; do sh -n "$file"; done
python3 - "$ROOT" <<'PY'
from pathlib import Path
import re
import subprocess
import sys
root = Path(sys.argv[1])
for directory in ('tests', 'scripts'):
    for path in (root / directory).rglob('*.py'):
        compile(path.read_text(), str(path), 'exec')
assert (root / 'external.desc').read_text().splitlines()[0] == 'name: ELO_OS'
assert 'source "$BR2_EXTERNAL_ELO_OS_PATH/package/elo-client/Config.in"' in (root / 'Config.in').read_text()
assert re.fullmatch(r'\d+\.\d+\.\d+\n?', (root / 'VERSION').read_text())
assert (root / 'LICENSE').read_bytes() == (root / 'package/elo-client/src/COPYING').read_bytes() == (root / 'board/elo/common/rootfs-overlay/usr/share/licenses/elo-os/COPYING').read_bytes()
assert 'VERSION=2026.08.1' in (root / 'scripts/profiles.sh').read_text()
for name in ('README.md', 'docs/tests/acceptance.md', 'docs/tests/implementation-review.md', 'tests/boot/README.md', 'tests/boot/pi5-first-boot.md', 'tests/boot/pi5-evidence-template.md', 'tests/client/README.md', 'docs/adr/ADR-009-local-client.md', 'docs/tests/desktop-validation.md', 'docs/client/local-contracts.md', 'docs/tests/p2-client-review.md', 'docs/tests/appliance-validation.md', 'docs/ELO-OS-IMPL-003_v0.1.0.md'):
    document = root / name
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', document.read_text()):
        if '://' not in target and not target.startswith('#'):
            assert (document.parent / target.split('#')[0]).exists(), f'Link local inválido em {name}: {target}'
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
for name in filter(None, tracked):
    if name.startswith(('output/', '.cache/', 'secrets/')) or name.endswith(('.img', '.qcow2', '.vfat', '.ext4', '.key', '.p12', '.pfx')):
        raise SystemExit(f'Artefato/segredo indevido no Git: {name}')
    path = root / name
    if path.is_file() and path.stat().st_size < 1000000 and re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', path.read_bytes()):
        raise SystemExit(f'Chave privada no Git: {name}')
print('PASS Q0-static: estrutura, sintaxe shell/Python e integração externa; NÃO comprova build/boot')
PY
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/boot/pi5-preflight-test.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/client/local-content-test.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/client/elo-import-test.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/client/supervisor-test.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/recovery/data-image-test.py"

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/network/pi5-tools-test.py"

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/network/panel-test.py"

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/client/terminal-setup-test.py"
