#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VERSION=2026.08.1
BR_DIR=${BUILDROOT_DIR:-"$ROOT/.cache/buildroot-$VERSION"}
OUT_DIR=${OUTPUT_DIR:-"$ROOT/output/pi5"}
[[ -f "$BR_DIR/Makefile" ]] || { echo 'Primeiro execute scripts/build.sh' >&2; exit 1; }
[[ -f "$OUT_DIR/.config" ]] || { echo 'Sem .config: execute scripts/build.sh antes' >&2; exit 1; }
make -C "$BR_DIR" O="$OUT_DIR" BR2_EXTERNAL="$ROOT" menuconfig
