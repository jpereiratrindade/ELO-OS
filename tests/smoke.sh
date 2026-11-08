#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
for file in   "$ROOT/README.md" "$ROOT/VERSION" "$ROOT/external.desc"   "$ROOT/external.mk" "$ROOT/Config.in"   "$ROOT/configs/elo_pi5_defconfig"   "$ROOT/board/elo/pi5/rootfs-overlay/etc/elo-os-release"   "$ROOT/docs/ELO-OS-BASES-001_v0.1.0.md"   "$ROOT/package/elo-client/Config.in" "$ROOT/package/elo-client/elo-client.mk"; do
  test -s "$file" || { echo "ERRO: faltando $file" >&2; exit 1; }
done
for file in "$ROOT"/scripts/*.sh "$ROOT"/board/elo/pi5/*.sh; do
  bash -n "$file" || { echo "Erro de sintaxe shell: $file" >&2; exit 1; }
done
grep -q '^name: ELO_OS$' "$ROOT/external.desc"
grep -q 'BR2_aarch64=y' "$ROOT/configs/elo_pi5_defconfig"
grep -q '2026.08.1' "$ROOT/scripts/build.sh"
echo 'PASS: integridade do scaffold e sintaxe shell (NÃO comprova build/boot)'
