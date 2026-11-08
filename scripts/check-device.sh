#!/usr/bin/env bash
# Diagnóstico opt-in. Não habilita SSH no dispositivo.
set -Eeuo pipefail
[[ $# -eq 1 ]] || { echo 'Uso: check-device.sh usuario@host' >&2; exit 2; }
ssh -o BatchMode=yes -- "$1" 'uname -a; cat /etc/elo-os-release 2>/dev/null || true; ls /dev/dri 2>/dev/null || true; uptime'
