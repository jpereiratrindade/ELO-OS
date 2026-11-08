#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUT_DIR=${OUTPUT_DIR:-"$ROOT/output/qemu-x86_64"}
QEMU=${QEMU:-qemu-system-x86_64}
command -v "$QEMU" >/dev/null || {
  echo 'QEMU ausente. No Fedora: sudo dnf install qemu-system-x86-core' >&2
  exit 1
}
for image in bzImage rootfs.ext4; do
  [[ -f "$OUT_DIR/images/$image" ]] || {
    echo "Imagem ausente: $OUT_DIR/images/$image" >&2
    echo 'Execute: PROFILE=qemu-x86_64 ./scripts/build.sh' >&2
    exit 1
  }
done
# A snapshot keeps the base image intact; guest writes disappear on exit.
# User networking provides DHCP without root privileges or a host bridge.
ACCEL=${QEMU_ACCEL:-tcg}
if [[ -z ${QEMU_ACCEL:-} && $(uname -m) == x86_64 && -r /dev/kvm && -w /dev/kvm ]]; then
  ACCEL=kvm
fi
echo "ELO/OS :: QEMU x86_64 ($ACCEL); login: root; sair: Ctrl-a x" >&2
exec "$QEMU" \
  -machine pc -accel "$ACCEL" -m "${QEMU_MEMORY:-512M}" -smp "${QEMU_CPUS:-2}" \
  -kernel "$OUT_DIR/images/bzImage" \
  -drive "file=$OUT_DIR/images/rootfs.ext4,if=virtio,format=raw,snapshot=on" \
  -append 'rootwait root=/dev/vda console=ttyS0' \
  -nic user,model=virtio-net-pci \
  -display none -serial mon:stdio -no-reboot "$@"
