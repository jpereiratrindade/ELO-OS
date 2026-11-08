#!/bin/sh
# Hook reservado para a etapa P2. Não incluído na defconfig P1.
set -eu
TARGET_DIR=${1:?uso: post-build.sh TARGET_DIR}
test -d "$TARGET_DIR" || { echo "TARGET_DIR inválido" >&2; exit 1; }
# Integrações futuras precisam ser idempotentes e não modificar o host.
