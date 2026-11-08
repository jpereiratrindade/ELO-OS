#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
IMAGES=${OUTPUT_DIR:-"$ROOT/output/pi5"}/images
[[ -d "$IMAGES" ]] || { echo "Nenhuma imagem em $IMAGES" >&2; exit 1; }
ls -lh "$IMAGES"
if [[ -f "$IMAGES/sdcard.img" ]]; then
  sha256sum "$IMAGES/sdcard.img"
else
  echo 'sdcard.img ausente' >&2
  exit 1
fi
