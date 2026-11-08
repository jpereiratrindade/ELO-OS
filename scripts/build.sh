#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VERSION=2026.08.1
BR_DIR=${BUILDROOT_DIR:-"$ROOT/.cache/buildroot-$VERSION"}
PROFILE=${PROFILE:-pi5}
case "$PROFILE" in
  pi5) DEFCONFIG=elo_pi5_defconfig; IMAGE=sdcard.img ;;
  qemu-x86_64) DEFCONFIG=elo_qemu_x86_64_defconfig; IMAGE=bzImage ;;
  *) echo "Perfil desconhecido: $PROFILE (use pi5 ou qemu-x86_64)" >&2; exit 2 ;;
esac
OUT_DIR=${OUTPUT_DIR:-"$ROOT/output/$PROFILE"}
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

if [[ ! -f "$OUT_DIR/.config" ]]; then
  echo "Configurando perfil ELO $PROFILE ..."
  make -C "$BR_DIR" O="$OUT_DIR" BR2_EXTERNAL="$ROOT" "$DEFCONFIG"
else
  configured=$(sed -n 's/^BR2_DEFCONFIG="\(.*\)"/\1/p' "$OUT_DIR/.config")
  if [[ "$configured" != "$ROOT/configs/$DEFCONFIG" ]]; then
    echo "ERRO: $OUT_DIR usa outra defconfig: $configured" >&2
    echo 'Escolha um OUTPUT_DIR separado para este perfil.' >&2
    exit 1
  fi
  echo "Reutilizando configuração existente em $OUT_DIR/.config"
  printf 'Para reaplicar a defconfig: make -C %q O=%q BR2_EXTERNAL=%q %q\n' "$BR_DIR" "$OUT_DIR" "$ROOT" "$DEFCONFIG"
fi

echo "Compilando Buildroot: $VERSION · jobs=$JOBS"
make -C "$BR_DIR" O="$OUT_DIR" BR2_EXTERNAL="$ROOT" -j "$JOBS"
echo "Verifique a imagem em: $OUT_DIR/images/$IMAGE"
