#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PROFILE=${PROFILE:-pi5}
source "$ROOT/scripts/profiles.sh"
check_profile_config
IMAGES="$OUT_DIR/images"
[[ -d "$IMAGES" ]] || { echo "Nenhuma imagem em $IMAGES" >&2; exit 1; }
ls -lh "$IMAGES"
for artifact in "${artifacts[@]}"; do
  [[ -f "$IMAGES/$artifact" ]] || { echo "$artifact ausente" >&2; exit 1; }
  sha256sum "$IMAGES/$artifact"
done
