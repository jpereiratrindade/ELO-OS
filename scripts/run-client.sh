#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CLIENT_BUILD_DIR=${CLIENT_BUILD_DIR:-"$ROOT/build/client-fedora"}
cmake -S "$ROOT/package/elo-client/src" -B "$CLIENT_BUILD_DIR" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DELO_BUILD_GUI=ON -DELO_BUILD_TESTS=ON
cmake --build "$CLIENT_BUILD_DIR" --parallel "${JOBS:-2}"
export QT_QUICK_BACKEND=${QT_QUICK_BACKEND:-software}
exec "$CLIENT_BUILD_DIR/elo-client" "$@"
