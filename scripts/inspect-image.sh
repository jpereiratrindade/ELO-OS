#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PROFILE=${PROFILE:-pi5}
case "$PROFILE" in
  pi5) artifacts=(sdcard.img) ;;
  qemu-x86_64) artifacts=(bzImage rootfs.ext4) ;;
  *) echo "Perfil desconhecido: $PROFILE" >&2; exit 2 ;;
esac
IMAGES=${OUTPUT_DIR:-"$ROOT/output/$PROFILE"}/images
[[ -d "$IMAGES" ]] || { echo "Nenhuma imagem em $IMAGES" >&2; exit 1; }
ls -lh "$IMAGES"
for artifact in "${artifacts[@]}"; do
  [[ -f "$IMAGES/$artifact" ]] || { echo "$artifact ausente" >&2; exit 1; }
  sha256sum "$IMAGES/$artifact"
done
