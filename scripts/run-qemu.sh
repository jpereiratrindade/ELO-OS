#!/usr/bin/env bash
set -Eeuo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PROFILE=${PROFILE:-qemu-x86_64}
source "$ROOT/scripts/profiles.sh"
case "$PROFILE" in
  qemu-x86_64|qemu-x86_64-gui|qemu-x86_64-appliance) QEMU=${QEMU:-qemu-system-x86_64}; FEDORA_PACKAGE=qemu-system-x86-core ;;
  qemu-aarch64|qemu-aarch64-gui|qemu-aarch64-appliance) QEMU=${QEMU:-qemu-system-aarch64}; FEDORA_PACKAGE=qemu-system-aarch64-core ;;
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
  # PCI ordering keeps root/data enumeration stable with two appliance disks.
  if [[ "$APPLIANCE" == 1 ]]; then devices[3]=virtio-blk-pci,drive=hd0; fi
  network=(-netdev user,id=net0 -device virtio-net-device,netdev=net0)
else
  machine=(-machine pc)
  devices=(-drive "file=$OUT_DIR/images/rootfs.ext4,if=virtio,format=raw,snapshot=on")
  if [[ "$APPLIANCE" == 1 ]]; then
    devices=(-drive "file=$OUT_DIR/images/rootfs.ext4,if=none,format=raw,id=hd0,snapshot=on"
      -device virtio-blk-pci,drive=hd0)
  fi
  network=(-nic user,model=virtio-net-pci)
fi
if [[ "$APPLIANCE" == 1 ]]; then
  case "${QEMU_DATA:-on}" in
    on)
      data_image=$(realpath -m "${QEMU_DATA_IMAGE:-"$OUT_DIR/data.ext4"}")
      [[ -f "$data_image" && -r "$data_image" && -w "$data_image" && "$data_image" != *,* ]] || {
        echo 'Disco de dados deve ser arquivo regular legível/gravável, com caminho sem vírgulas.' >&2
        echo 'Crie um arquivo novo com scripts/create-data-image.sh ou use QEMU_DATA=off para testar ausência.' >&2
        exit 1
      }
      [[ ! "$data_image" -ef "$OUT_DIR/images/rootfs.ext4" && ! "$data_image" -ef "$OUT_DIR/images/$KERNEL" ]] || {
        echo 'Disco de dados não pode ser um artefato do sistema.' >&2; exit 1;
      }
      devices+=(-drive "file=$data_image,if=none,format=raw,id=elo-data"
        -device virtio-blk-pci,drive=elo-data)
      echo "ELO/OS :: dados persistentes em arquivo: $data_image" >&2
      ;;
    off) echo 'ELO/OS :: disco de dados ausente por solicitação de teste' >&2 ;;
    *) echo 'QEMU_DATA deve ser on ou off.' >&2; exit 2 ;;
  esac
fi
case "${QEMU_NETWORK:-user}" in
  user) ;;
  off) network=(-nic none) ;;
  *) echo 'QEMU_NETWORK deve ser user ou off.' >&2; exit 2 ;;
esac
display=(-display none)
memory=512M
if [[ "$GRAPHICS" == 1 ]]; then
  if [[ ${QEMU_NETWORK:-user} == user ]]; then
    if [[ "$ARCH" == aarch64 ]]; then net_device=virtio-net-device; else net_device=virtio-net-pci; fi
    network=(-netdev user,id=net0 -device "$net_device,netdev=net0,id=elo-net")
  fi
  memory=1024M
  display=(-display "${QEMU_DISPLAY:-gtk}" -device virtio-gpu-pci,xres=1024,yres=768
    -device virtio-keyboard-pci -device virtio-mouse-pci)
  if [[ "$ARCH" == x86_64 ]]; then display+=(-vga none); fi
fi
echo "ELO/OS :: PROFILE=$PROFILE · ARCH=$ARCH · ACCEL=$ACCEL · CONSOLE=$CONSOLE · root=/dev/vda · snapshot=on" >&2
echo 'Bancada local: login root sem senha; desligar: poweroff; sair do QEMU: Ctrl-a x' >&2
boot_args="rootwait root=/dev/vda console=$CONSOLE"
[[ "$APPLIANCE" == 0 ]] || boot_args+=' ro'
exec "$QEMU" "${machine[@]}" -accel "$ACCEL" -m "${QEMU_MEMORY:-$memory}" -smp "${QEMU_CPUS:-2}" \
  -kernel "$OUT_DIR/images/$KERNEL" "${devices[@]}" "${network[@]}" \
  -append "$boot_args" "${display[@]}" -serial mon:stdio -no-reboot "$@"
