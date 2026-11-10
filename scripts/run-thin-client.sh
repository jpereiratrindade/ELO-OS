#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Fedora development launcher for the local HTTPS distribution daemon.
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ELO_SERVER_URL=${ELO_SERVER_URL:-https://localhost:8443/v1/presentation}
ELO_CONTENT_DIR=${ELO_CONTENT_DIR:-"$HOME/.local/share/elo-client/content"}
ELO_CLIENT_TOKEN_FILE=${ELO_CLIENT_TOKEN_FILE:-"$HOME/.config/elo-distribution/terminal.token"}
ELO_SERVER_CA_FILE=${ELO_SERVER_CA_FILE-"$HOME/.config/elo-distribution/server.crt"}
mkdir -p "$(dirname "$ELO_CONTENT_DIR")"
arguments=(--server "$ELO_SERVER_URL" --content-dir "$ELO_CONTENT_DIR" --token-file "$ELO_CLIENT_TOKEN_FILE")
if [[ -n "$ELO_SERVER_CA_FILE" ]]; then arguments+=(--ca-file "$ELO_SERVER_CA_FILE"); fi
exec "$ROOT/scripts/run-client.sh" "${arguments[@]}" "$@"
