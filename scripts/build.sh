#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PROFILE=${PROFILE:-pi5}
source "$ROOT/scripts/profiles.sh"
JOBS=${JOBS:-8}

command -v git >/dev/null || { echo 'git não encontrado' >&2; exit 1; }
command -v make >/dev/null || { echo 'make não encontrado' >&2; exit 1; }
if [[ ! -f "$BR_DIR/Makefile" ]]; then
  if [[ -e "$BR_DIR" ]]; then
    echo "ERRO: $BR_DIR existe, mas não contém Makefile do Buildroot" >&2
    exit 1
  fi
  echo "Clonando Buildroot release fixa $VERSION (sem alterar outros projetos)..."
  mkdir -p "$(dirname "$BR_DIR")"
  git clone --depth 1 --branch "$VERSION" https://gitlab.com/buildroot.org/buildroot.git "$BR_DIR"
fi

grep -qx "export BR2_VERSION := $VERSION" "$BR_DIR/Makefile" || {
  echo "Buildroot incorreto em $BR_DIR: esperado $VERSION" >&2; exit 1;
}
printf 'PROFILE=%s · ARCH=%s · Buildroot=%s · jobs=%s\nBR2_EXTERNAL=%s\nO=%s\n' "$PROFILE" "$ARCH" "$VERSION" "$JOBS" "$ROOT" "$OUT_DIR"
if [[ ! -f "$OUT_DIR/.config" ]]; then
  echo "Configurando perfil ELO $PROFILE ..."
  make -C "$BR_DIR" O="$OUT_DIR" BR2_EXTERNAL="$ROOT" "$DEFCONFIG"
else
  check_profile_config
  echo "Reutilizando configuração existente em $OUT_DIR/.config"
  printf 'Para reaplicar a defconfig: make -C %q O=%q BR2_EXTERNAL=%q %q\n' "$BR_DIR" "$OUT_DIR" "$ROOT" "$DEFCONFIG"
fi

echo "Compilando Buildroot: $VERSION · jobs=$JOBS"
make -C "$BR_DIR" O="$OUT_DIR" BR2_EXTERNAL="$ROOT" -j "$JOBS"
printf 'Verifique: %s/images/%s\n' "$OUT_DIR" "${artifacts[0]}"
