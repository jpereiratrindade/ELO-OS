#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# Same terminal configuration on desktop and embedded Linux. No shell sourcing.
set -eu
config=${ELO_TERMINAL_CONFIG:-/etc/elo-terminal}
content=${ELO_CONTENT_DIR:-/var/lib/elo-client/content}
client=${ELO_CLIENT_BIN:-/usr/bin/elo-client}
[ -s "$config/server.url" ] || { echo 'Terminal ELO sem configuração do servidor' >&2; exit 2; }
endpoint=$(cat "$config/server.url")
case "$endpoint" in https://*) ;; *) echo 'Terminal ELO requer HTTPS' >&2; exit 2 ;; esac
[ -f "$config/terminal.token" ] || { echo 'Credencial do terminal ausente' >&2; exit 2; }
set -- --fullscreen --content-dir "$content" --server "$endpoint" --token-file "$config/terminal.token" "$@"
if [ -f "$config/ca.pem" ]; then set -- "$@" --ca-file "$config/ca.pem"; fi
exec "$client" "$@"
