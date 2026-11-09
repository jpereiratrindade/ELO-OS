#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
target=${1:?Buildroot target directory required}
mkdir -p "$target/data" "$target/usr/libexec"
chmod 0755 "$target/data"
# Keep the P2 service unchanged; the appliance wrapper supplies volatile caches.
install -m 0755 "$ROOT/board/elo/qemu-gui/rootfs-overlay/etc/init.d/S50elo-client" \
  "$target/usr/libexec/elo-client-service"
# The application starts before DHCP, including its bounded missing-NIC wait.
if [[ -f "$target/etc/init.d/S40network" ]]; then
  mv -f "$target/etc/init.d/S40network" "$target/etc/init.d/S60network"
fi
python3 "$ROOT/scripts/image-build-info.py" "$target"
test -x "$target/etc/init.d/S60network"
if grep -Eq '^[^#].*mount -o remount,rw /$' "$target/etc/inittab"; then
  echo 'Appliance must not remount root read-write' >&2
  exit 1
fi
