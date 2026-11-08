#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PROFILE=${PROFILE:-pi5}
source "$ROOT/scripts/profiles.sh"
[[ -f "$BR_DIR/Makefile" ]] || { echo 'Primeiro execute scripts/build.sh' >&2; exit 1; }
[[ -f "$OUT_DIR/.config" ]] || { echo 'Sem .config: execute scripts/build.sh antes' >&2; exit 1; }
check_profile_config
make -C "$BR_DIR" O="$OUT_DIR" BR2_EXTERNAL="$ROOT" menuconfig
