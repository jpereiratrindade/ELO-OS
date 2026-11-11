#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Development launcher. Does not install a service or enable camera automatically.
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CONTAINER=${ELO_AV_CONTAINER:-elo-os}
exec toolbox run -c "$CONTAINER" env \
  ELO_ENABLE_MULTIMEDIA=ON ELO_ENABLE_VISION=ON \
  CLIENT_BUILD_DIR="$ROOT/build/client-av" \
  "$ROOT/scripts/run-thin-client.sh" "$@"
