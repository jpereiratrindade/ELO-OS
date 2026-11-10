#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Desktop bench: build once, then supervise rendered frames and recover unattended.
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CLIENT_BUILD_DIR=${CLIENT_BUILD_DIR:-"$ROOT/build/client-fedora"}
ELO_SERVER_URL=${ELO_SERVER_URL:-https://localhost:8443/v1/presentation}
ELO_CONTENT_DIR=${ELO_CONTENT_DIR:-"$HOME/.local/share/elo-client/content"}
ELO_CLIENT_TOKEN_FILE=${ELO_CLIENT_TOKEN_FILE:-"$HOME/.config/elo-distribution/terminal.token"}
ELO_SERVER_CA_FILE=${ELO_SERVER_CA_FILE-"$HOME/.config/elo-distribution/server.crt"}
ELO_RUNTIME_DIR=${ELO_RUNTIME_DIR:-"${XDG_RUNTIME_DIR:?Graphical session runtime required}/elo-client"}
export ELO_RUNTIME_DIR
cmake -S "$ROOT/package/elo-client/src" -B "$CLIENT_BUILD_DIR" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DELO_BUILD_GUI=ON -DELO_BUILD_TESTS=ON
cmake --build "$CLIENT_BUILD_DIR" --parallel "${JOBS:-2}"
export QT_QUICK_BACKEND=${QT_QUICK_BACKEND:-software}
arguments=(--fullscreen --server "$ELO_SERVER_URL" --content-dir "$ELO_CONTENT_DIR" --token-file "$ELO_CLIENT_TOKEN_FILE")
if [[ -n "$ELO_SERVER_CA_FILE" ]]; then arguments+=(--ca-file "$ELO_SERVER_CA_FILE"); fi
exec "$ROOT/board/elo/qemu-gui/rootfs-overlay/usr/bin/elo-client-supervisor" \
  "$CLIENT_BUILD_DIR/elo-client" "${arguments[@]}" "$@"
