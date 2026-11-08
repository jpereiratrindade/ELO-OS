#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PROFILE=${PROFILE:-qemu-x86_64}
source "$ROOT/scripts/profiles.sh"
case "$PROFILE" in
  qemu-x86_64|qemu-x86_64-gui) QEMU=${QEMU:-qemu-system-x86_64}; FEDORA_PACKAGE=qemu-system-x86-core ;;
  qemu-aarch64|qemu-aarch64-gui) QEMU=${QEMU:-qemu-system-aarch64}; FEDORA_PACKAGE=qemu-system-aarch64-core ;;
  *) echo 'Use um perfil QEMU para iniciar uma VM.' >&2; exit 2 ;;
esac
check_profile_config
command -v "$QEMU" >/dev/null || {
  echo "QEMU ausente. No Fedora: sudo dnf install $FEDORA_PACKAGE (ou informe QEMU=/caminho/do/binário)" >&2
  exit 1
}
for image in "$KERNEL" rootfs.ext4; do
  [[ -f "$OUT_DIR/images/$image" ]] || {
    echo "Imagem ausente: $OUT_DIR/images/$image" >&2
    echo "Execute: PROFILE=$PROFILE ./scripts/build.sh" >&2
    exit 1
  }
done
# A snapshot keeps the base image intact; guest writes disappear on exit.
# User networking provides DHCP without root privileges or a host bridge.
ACCEL=${QEMU_ACCEL:-tcg}
if [[ "$ARCH" == x86_64 && -z ${QEMU_ACCEL:-} && $(uname -m) == x86_64 && -r /dev/kvm && -w /dev/kvm ]]; then
  ACCEL=kvm
fi
if [[ "$ARCH" == aarch64 ]]; then
  [[ "$ACCEL" == tcg ]] || { echo 'O perfil ARM64 de bancada usa TCG.' >&2; exit 2; }
  machine=(-machine virt -cpu cortex-a53)
  devices=(-drive "file=$OUT_DIR/images/rootfs.ext4,if=none,format=raw,id=hd0,snapshot=on"
    -device virtio-blk-device,drive=hd0)
  network=(-netdev user,id=net0 -device virtio-net-device,netdev=net0)
else
  machine=(-machine pc)
  devices=(-drive "file=$OUT_DIR/images/rootfs.ext4,if=virtio,format=raw,snapshot=on")
  network=(-nic user,model=virtio-net-pci)
fi
case "${QEMU_NETWORK:-user}" in
  user) ;;
  off) network=(-nic none) ;;
  *) echo 'QEMU_NETWORK deve ser user ou off.' >&2; exit 2 ;;
esac
display=(-display none)
memory=512M
if [[ "$GRAPHICS" == 1 ]]; then
  memory=1024M
  display=(-display "${QEMU_DISPLAY:-gtk}" -device virtio-gpu-pci,xres=1024,yres=768
    -device virtio-keyboard-pci -device virtio-mouse-pci)
  if [[ "$ARCH" == x86_64 ]]; then display+=(-vga none); fi
fi
echo "ELO/OS :: PROFILE=$PROFILE · ARCH=$ARCH · ACCEL=$ACCEL · CONSOLE=$CONSOLE · root=/dev/vda · snapshot=on" >&2
echo 'Bancada local: login root sem senha; desligar: poweroff; sair do QEMU: Ctrl-a x' >&2
exec "$QEMU" "${machine[@]}" -accel "$ACCEL" -m "${QEMU_MEMORY:-$memory}" -smp "${QEMU_CPUS:-2}" \
  -kernel "$OUT_DIR/images/$KERNEL" "${devices[@]}" "${network[@]}" \
  -append "rootwait root=/dev/vda console=$CONSOLE" "${display[@]}" -serial mon:stdio -no-reboot "$@"
