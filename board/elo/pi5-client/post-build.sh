#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# External boot files must refresh even when cached rpi-firmware is not rebuilt.
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
: "${BINARIES_DIR:?Buildroot image directory required}"
install -D -m 0644 "$ROOT/board/elo/pi5-client/cmdline.txt" "$BINARIES_DIR/rpi-firmware/cmdline.txt"
install -D -m 0644 "$ROOT/board/elo/pi5-client/config.txt" "$BINARIES_DIR/rpi-firmware/config.txt"
python3 "$ROOT/scripts/pi5-image-variant.py" "$1"
