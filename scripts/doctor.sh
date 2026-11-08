#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
echo 'ELO/OS :: Diagnóstico do host'
echo "Repositório: $ROOT"
for x in git make gcc g++ python3 rsync tar awk sed xz gzip base64; do
  if command -v "$x" >/dev/null 2>&1; then printf '  OK  %s
' "$x";
  else printf '  --  %s ausente
' "$x"; fi
done
if [[ -f "$ROOT/.cache/buildroot-2026.08.1/Makefile" ]]; then
  echo 'Buildroot fixado: disponível'
else
  echo 'Buildroot fixado: ainda não baixado (normal antes do build)'
fi
if command -v qemu-system-x86_64 >/dev/null 2>&1; then
  echo 'QEMU x86_64: disponível'
  if [[ -r /dev/kvm && -w /dev/kvm ]]; then
    echo 'KVM: acessível'
  else
    echo 'KVM: indisponível para este usuário; QEMU pode usar TCG'
  fi
else
  echo 'QEMU x86_64: ausente (opcional; Fedora: sudo dnf install qemu-system-x86-core)'
fi
if [[ -e "$ROOT/output/pi5/images/sdcard.img" ]]; then
  echo 'Imagem Pi 5: existe (não implica teste físico)'
else
  echo 'Imagem Pi 5: ainda não compilada'
fi
