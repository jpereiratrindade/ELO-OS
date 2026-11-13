#!/usr/bin/env bash
# Shared host-side profile selection. The caller sets ROOT and a default PROFILE.
VERSION=2026.08.1
GRAPHICS=0
APPLIANCE=0
case "$PROFILE" in
  pi5-client-vision) DEFCONFIG=elo_pi5_client_vision_defconfig; ARCH=aarch64; KERNEL=Image; artifacts=(sdcard.img); CONSOLE=ttyAMA10; GRAPHICS=1 ;;
  pi5-client) DEFCONFIG=elo_pi5_client_defconfig; ARCH=aarch64; KERNEL=Image; artifacts=(sdcard.img); CONSOLE=ttyAMA10; GRAPHICS=1 ;;
  pi5) DEFCONFIG=elo_pi5_defconfig; ARCH=aarch64; KERNEL=Image; artifacts=(sdcard.img); CONSOLE=ttyAMA10 ;;
  qemu-x86_64) DEFCONFIG=elo_qemu_x86_64_defconfig; ARCH=x86_64; KERNEL=bzImage; artifacts=(bzImage rootfs.ext4); CONSOLE=ttyS0 ;;
  qemu-aarch64) DEFCONFIG=elo_qemu_aarch64_defconfig; ARCH=aarch64; KERNEL=Image; artifacts=(Image rootfs.ext4); CONSOLE=ttyAMA0 ;;
  qemu-x86_64-gui) DEFCONFIG=elo_qemu_x86_64_gui_defconfig; ARCH=x86_64; KERNEL=bzImage; artifacts=(bzImage rootfs.ext4); CONSOLE=ttyS0; GRAPHICS=1 ;;
  qemu-aarch64-gui) DEFCONFIG=elo_qemu_aarch64_gui_defconfig; ARCH=aarch64; KERNEL=Image; artifacts=(Image rootfs.ext4); CONSOLE=ttyAMA0; GRAPHICS=1 ;;
  qemu-x86_64-appliance) DEFCONFIG=elo_qemu_x86_64_appliance_defconfig; ARCH=x86_64; KERNEL=bzImage; artifacts=(bzImage rootfs.ext4); CONSOLE=ttyS0; GRAPHICS=1; APPLIANCE=1 ;;
  qemu-aarch64-appliance) DEFCONFIG=elo_qemu_aarch64_appliance_defconfig; ARCH=aarch64; KERNEL=Image; artifacts=(Image rootfs.ext4); CONSOLE=ttyAMA0; GRAPHICS=1; APPLIANCE=1 ;;
  *) echo "Perfil desconhecido: $PROFILE (use pi5, pi5-client ou perfis QEMU console, -gui ou -appliance)" >&2; exit 2 ;;
esac
BR_DIR=${BUILDROOT_DIR:-"$ROOT/.cache/buildroot-$VERSION"}
OUT_DIR=$(realpath -m "${OUTPUT_DIR:-"$ROOT/output/$PROFILE"}")

check_profile_config() {
  local configured
  [[ -f "$OUT_DIR/.config" ]] || { echo "Configuração ausente: $OUT_DIR/.config" >&2; return 1; }
  configured=$(sed -n 's/^BR2_DEFCONFIG="\(.*\)"/\1/p' "$OUT_DIR/.config")
  if [[ "$configured" != "$ROOT/configs/$DEFCONFIG" ]] || ! grep -qx "BR2_$ARCH=y" "$OUT_DIR/.config"; then
    echo "ERRO: $OUT_DIR não pertence ao perfil $PROFILE (defconfig: $configured)" >&2
    echo 'Escolha um OUTPUT_DIR separado para este perfil.' >&2
    return 1
  fi
}
