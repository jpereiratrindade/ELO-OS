#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PROFILE=${PROFILE:-qemu-x86_64-appliance}
source "$ROOT/scripts/profiles.sh"
[[ "$APPLIANCE" == 1 ]] || { echo 'Use um perfil -appliance.' >&2; exit 2; }
size=${DATA_SIZE_MIB:-128}
[[ "$size" =~ ^[1-9][0-9]{0,3}$ ]] && (( size >= 32 && size <= 4096 )) || {
  echo 'DATA_SIZE_MIB deve ser inteiro de 32 a 4096.' >&2; exit 2;
}
destination=${QEMU_DATA_IMAGE:-"$OUT_DIR/data.ext4"}
[[ ! -e "$destination" && ! -L "$destination" ]] || {
  echo "Recusando sobrescrever arquivo existente: $destination" >&2; exit 1;
}
mkfs="$OUT_DIR/host/sbin/mkfs.ext4"
if [[ ! -x "$mkfs" ]]; then
  mkfs=$(command -v mkfs.ext4) || { echo 'mkfs.ext4 ausente; conclua o build ou instale e2fsprogs na Toolbox.' >&2; exit 1; }
fi
directory=$(dirname "$destination")
mkdir -p "$directory"
temporary=$(mktemp "$directory/.elo-data.XXXXXXXX")
trap 'rm -f "$temporary"' EXIT
truncate -s "${size}M" "$temporary"
"$mkfs" -q -L ELO_DATA -m 0 -O '^64bit' "$temporary"
python3 - "$temporary" "$destination" <<'PY'
import os
import sys
from pathlib import Path
source, destination = map(Path, sys.argv[1:])
with source.open('rb') as stream:
    os.fsync(stream.fileno())
# link publishes without replacing an existing file, including a racing creator.
os.link(source, destination)
try:
    descriptor = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
except OSError:
    print('Imagem publicada, mas durabilidade incerta; arquivo pode já existir.', file=sys.stderr)
    sys.exit(3)
PY
printf 'Disco de dados virtual criado: %s (%s MiB); nenhum dispositivo físico gravado.\n' "$destination" "$size"
