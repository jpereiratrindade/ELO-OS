#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VERSION=2026.08.1
BR_DIR=${BUILDROOT_DIR:-"$ROOT/.cache/buildroot-$VERSION"}
OUT_DIR=${OUTPUT_DIR:-"$ROOT/output/pi5"}
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
  echo 'Configurando perfil ELO Pi 5 ...'
  make -C "$BR_DIR" O="$OUT_DIR" BR2_EXTERNAL="$ROOT" elo_pi5_defconfig
else
  echo 'Reutilizando configuração existente em output/pi5/.config'
  echo 'Se alterar a defconfig, rode: make -C "$BR_DIR" O="$OUT_DIR" BR2_EXTERNAL="$ROOT" elo_pi5_defconfig'
fi

echo "Compilando Buildroot: $VERSION · jobs=$JOBS"
make -C "$BR_DIR" O="$OUT_DIR" BR2_EXTERNAL="$ROOT" -j "$JOBS"
echo "Verifique a imagem em: $OUT_DIR/images/sdcard.img"
